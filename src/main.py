
from enum import Enum
import mathutils

import bpy


class Direction(Enum):
    Up = mathutils.Vector((0, 1, 0))
    Left = mathutils.Vector((-1, 0, 0))
    Down = mathutils.Vector((0, -1, 0))
    Right = mathutils.Vector((1, 0, 0))

    def to_rotation(self):
        return Rotation[self.name]


class Rotation(Enum):
    Up = (1, 0, 0, 1)
    Left = (0, -1, 1, 0)
    Down = (-1, 0, 0, -1)
    Right = (0, 1, -1, 0)

    def to_direction(self):
        return Direction[self.name]

    def __add__(self, other):
        rotations = list(Rotation)
        return rotations[(rotations.index(self) + rotations.index(other)) % len(rotations)]


def clear_collection(collection):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in collection.objects:
        obj.select_set(True)
    bpy.ops.object.delete()

def get_group_vertices(module, group_name):
    group = module.vertex_groups[group_name]

    def is_in_group(vertex):
        return group.index in map(lambda group: group.group, vertex.groups)

    return list(filter(is_in_group, module.data.vertices))

def get_group_vectors(module, group_name):

    vertices = get_group_vertices(module, group_name)

    def to_vector(vertex):
        return module.matrix_world @ vertex.co

    return list(map(to_vector, vertices))

def apply_transformation(module, rotation, location=mathutils.Vector((0, 0, 0))):
    if not isinstance(location, mathutils.Vector):
        raise TypeError
    if not isinstance(rotation, Rotation):
        raise TypeError
    m = mathutils.Matrix()
    m[0][0], m[0][1], m[1][0], m[1][1] = rotation.value
    m[0][3], m[1][3], m[2][3] = location
    m[0][2], m[1][2], m[2][0], m[2][1] = 0, 0, 0, 0
    m[2][2] = 1
    module.matrix_world = m


class ModuleState:

    def __init__(self, module, rotation):
        self.module = module
        self.rotation = rotation

    def __eq__(self, other):
        return self.module.name == other.module.name and self.rotation is other.rotation

    def __hash__(self):
        return hash(self.module.name + self.rotation.name)

    @staticmethod
    def get_all_states(modules, states=set()):
        if states:
            return states.copy()
        states.update([ModuleState(module, rotation) for rotation in Rotation for module in modules])
        return states.copy()


class ModuleRuleManager:

    def __init__(self, modules):
        self.modules = modules
        self.rules = {}

    def compute_rules(self, module):

        def is_valid(adjacent_module):

            def to_frozen_vector(vector):
                return vector.freeze()

            for vertex_group_name, required_matches in (("wall", 3), ("floor", 2), ("void", 2)):
                try:
                    vectors = get_group_vectors(module, vertex_group_name)
                    adjacent_vectors = get_group_vectors(adjacent_module, vertex_group_name)
                except KeyError:
                    continue
                frozen_vectors = map(to_frozen_vector, vectors)
                frozen_adjacent_vectors = map(to_frozen_vector, adjacent_vectors)
                if len(set(frozen_vectors) & set(frozen_adjacent_vectors)) == required_matches:
                    break
            else:
                return False
            return True

        for adjacent_module in self.modules:
            adjacent_module_copy = adjacent_module.copy()
            adjacent_module_copy.name += "_copy"
            for direction in Direction:
                for rotation in Rotation:
                    location = module.location + direction.value
                    apply_transformation(adjacent_module_copy, rotation, location)
                    if is_valid(adjacent_module_copy):
                        if module not in self.rules:
                            self.rules[module] = {}
                        if direction not in self.rules[module]:
                            self.rules[module][direction] = set()
                        self.rules[module][direction].add(ModuleState(adjacent_module, rotation))

    def compute_all_rules(self):
        for module in self.modules:
            self.compute_rules(module)


class Slot:

    def __init__(self, x, y, collection):
        self.x = x
        self.y = y
        self.adjacent_slots = None
        self.valid_states = None
        self.rule_manager = None
        self.state = None
        self.collection = collection

    def set_adjacent_slots(self, adjacent_slots):
        self.adjacent_slots = adjacent_slots

    def set_valid_states(self, valid_states):
        self.valid_states = valid_states

    def set_rule_manager(self, rule_manager):
        self.rule_manager = rule_manager

    def is_collapsed(self):
        return self.state is not None

    def get_entropy(self):
        return len(self.valid_states)

    def compute_valid_states(self):
        for direction, adjacent_slot in self.adjacent_slots.items():
            if adjacent_slot is not None and not adjacent_slot.is_collapsed():
                continue
            elif adjacent_slot is None:
                module = bpy.data.collections["modules"].objects["void"]
                rotation = Rotation.Up
            else:
                module = adjacent_slot.state.module
                rotation = adjacent_slot.state.rotation

            base_rotations = [
                Rotation.Down,
                Rotation.Left,
                Rotation.Up,
                Rotation.Right
            ]

            rot_to_dir = dict(zip(Rotation, map(lambda r: (r+direction.to_rotation()).to_direction(), base_rotations)))
            adjacent_rules = self.rule_manager.rules[module][rot_to_dir[rotation]]
            rotated_adjacent_rules = {ModuleState(rule.module, rule.rotation+rotation) for rule in adjacent_rules}
            self.valid_states &= rotated_adjacent_rules

    def collapse(self):
        from random import choice
        if self.is_collapsed():
            return
        self.compute_valid_states()
        self.state = choice(list(self.valid_states))
        module = bpy.data.objects.new(f"({self.x}, {self.y})", self.state.module.data)
        apply_transformation(module, self.state.rotation, mathutils.Vector((self.x, self.y, 0)))
        self.collection.objects.link(module)


class Board:

    def __init__(self, width, height, collection):

        from itertools import starmap

        self.width = width
        self.height = height
        self.modules = None
        self.collection = collection

        self.slots = []
        for y in range(self.height):
            row = [Slot(x, y, self.collection) for x in range(self.width)]
            self.slots.append(row)

        def get_slot(x, y):
            if not (0 <= x < self.width and 0 <= y < self.height):
                return None
            return self.slots[y][x]

        for y in range(self.height):
            for x in range(self.width):
                adjacent_slots = dict(zip(Direction, starmap(get_slot, (map(int, (x+xd, y+yd)) for xd, yd, _ in map(lambda direction: direction.value, Direction)))))
                self.slots[y][x].set_adjacent_slots(adjacent_slots)

    def set_modules(self, modules):
        self.modules = modules
        self.rule_manager = ModuleRuleManager(self.modules)
        self.rule_manager.compute_all_rules()
        for row in self.slots:
            for slot in row:
                slot.set_valid_states(ModuleState.get_all_states(self.modules))
                slot.set_rule_manager(self.rule_manager)

    def fill(self):
        uncollapsed_slots = []
        for row in self.slots:
            for slot in row:
                if not slot.is_collapsed():
                    uncollapsed_slots.append(slot)
        while uncollapsed_slots:
            slot = min(uncollapsed_slots, key=lambda slot: slot.get_entropy())
            uncollapsed_slots.remove(slot)
            slot.collapse()

def main():

    modules = bpy.data.collections["modules"].objects

    collection = bpy.data.collections["board"]
    clear_collection(collection)
    board = Board(16, 16, collection)
    board.set_modules(modules)
    board.fill()

    scene = bpy.context.scene
    for frame in range(scene.frame_start, scene.frame_end+1):
        scene.frame_current = frame
        scene.render.filepath = "C:/tmp/" + str(scene.frame_current).zfill(3) + ".png"
        bpy.ops.render.render(False, animation=False, write_still=True)
        print(f"Rendered {scene.render.filepath}")


if __name__ == "__main__":
    main()
