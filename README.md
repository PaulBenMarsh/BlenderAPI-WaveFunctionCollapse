# BlenderAPI-WaveFunctionCollapse

A Python script which uses the Blender API to procedurally generate a simple interior environment using a an algorithm inspired by the popular "Wave Function Collapse" algorithm.
Given a collection of modules (simple 1x1x2 meshes that occupy one "tile" or "slot"), the script generates a set of rules for how every module is allowed to connect to other modules.
The rule-generation process is made possible by assigning specific vertices of each module to specific vertex groups, and then iterating through all possible module-to-module connection-permutations, creating a new rule if a given vertex group of two adjacent modules (in their current orientations) contain a set number of overlapping vertices.
Once all rules are generated, we create a "board" of "slots" (a "slot" is just a single open spot where a module can be placed), and we collapse every slot into a valid (according to the rules), known state.




<p align="center">
The five modules:<br>
<img src="https://github.com/PaulBenMarsh/BlenderAPI-WaveFunctionCollapse/blob/master/screenshots/five_modules.png?raw=true">
</p>

<p align="center">
<img src="https://github.com/PaulBenMarsh/BlenderAPI-WaveFunctionCollapse/blob/master/screenshots/board.png?raw=true">
</p>

Traditionally, as slots are being collapsed, to determine which slot should be collapsed next, one would find the slot with the least "entropy" - the slot with the lowest number of possible valids states into which it can collapse.
This is predicated on the fact that normally, one would update the valid, possible states of all slots after collapsing any given slot. In this code, I've elected to compute a given slots possible valid states only when it is being asked to collapse by looking at the state of its immediate, adjacent neighbor slots.
For this reason, the board isn't populated according to "lowest-entropy-first", unfortunately.

<p align="center">
<span>
<img src="https://github.com/PaulBenMarsh/BlenderAPI-WaveFunctionCollapse/blob/master/screenshots/loop_1.gif?raw=true">
<img src="https://github.com/PaulBenMarsh/BlenderAPI-WaveFunctionCollapse/blob/master/screenshots/loop_2.gif?raw=true">
</span>
</p>
