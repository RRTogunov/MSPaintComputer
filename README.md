## Background

What started as a joke about the worst way to do statistics, turned into an cognitive itch, and side hobby. 

I desigend a full set of logic gates that function natively within MS Paint using only the eye-dropper and the bucket/fill tools. These were combined to make an 8-bit ripple-carry adder as well as an 8-bit adder/subtractor circuit.

## Anatomy of a Logic Gate 

This is an example of the AND logic gate:

![Logic Gate Anatomy](media/logic_gate_anatomy.png)

The logic gate is executed as follows:
1. Define colors for A and B (white = 0, black  = 1). 
2. Using the colour-picker and bucket/fill tools, cycle through copy/pasting the colours from the logic/instruction sequence boxes on the left to their corresponding leads on the right. When there is more than one colour in the instruction, cycle through them from left to right. 

The following is a step-by-step execution of the above instruction for the AND gate:

![example_AND](media/example_AND_logic_gate.png)

## Full set of logic gates

The following is the full set of logic gates as well as bridges and buffers, which are used either to hold values to prevent back-propagation or to cross wires.

![example_AND](logic_gates.png)

## Example GIFs
Ripple-carry adder calculating 203 + 110 = 313 (in binary: 11001011 + 01101110 = 00111001 + carry 1):

![ripple](media/8_bit_ripple_adder.gif)

adder/subtractor calculating 10 + 3 = 13 (in binary: 1010 + 11 = 1101):

![Add/Sub 10+3](media/add_sub_10+3.gif)

Adder/subtractor calculating 8 - 3 = 5 (in binary: 1000 - 11 = 101):

![Add/Sub 8-3](media/add_sub_8-3.gif)


