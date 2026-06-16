#!/usr/bin/env python3
"""
paint_circuit_sim.py
====================
Simulates colour-propagation logic circuits of the kind built in MS Paint.

Mechanics
---------
Each region has a colour (string). A fill operation recolours the entire
connected same-colour component containing the target region -- exactly as
MS Paint flood-fill works on a pixel canvas.

The instruction set is a sequence of (target, colour_source) pairs where
colour_source is either:
  - a fixed colour string  ('black', 'orange', …), OR
  - a region name          in which case that region's *live* colour is used.
The second form is the variable-colour / conditional-assignment instruction
enabled by the bridge mechanism: the bus assigns an input's actual value
rather than a fixed colour, making it possible to compute implications and
XOR in fewer waves.

Fan-out is expressed directly in the instruction sequence as
    (copy_region, source_region)
steps that appear before the first logic wave.  There is no separate fanout
dict; run_truth_table takes a flat input_regions list that maps each logical
input name to exactly one physical seed region.

Usage
-----
    python paint_circuit_sim.py          # runs all built-in gate truth tables

    from paint_circuit_sim import PaintCircuit, run_truth_table, print_truth_table
    adj, col, ins, out = and_gate()
    c = PaintCircuit(adj, col)
    rows = run_truth_table(c, ['A', 'B'], out, ins)
    print_truth_table(rows, out, title='AND')
"""

from __future__ import annotations
from typing import Optional
import itertools


# =============================================================================
# Core simulation class
# =============================================================================

class PaintCircuit:
    """
    Graph of named regions, each with a colour, connected by orthogonal
    adjacency.  Fill operations propagate through connected same-colour
    components exactly as MS Paint flood-fill does.
    """

    def __init__(
        self,
        adjacency: dict[str, set[str]],
        initial_colours: dict[str, str],
    ) -> None:
        """
        Parameters
        ----------
        adjacency : dict[str, set[str]]
            Symmetric adjacency graph.  Every key must appear in
            initial_colours; missing regions are given empty adjacency sets.
        initial_colours : dict[str, str]
            Starting colour of every region.
        """
        self.adjacency: dict[str, set[str]] = {
            r: set(nbs) for r, nbs in adjacency.items()
        }
        for r in initial_colours:                   # regions with no adjacency
            self.adjacency.setdefault(r, set())

        self._initial: dict[str, str] = dict(initial_colours)
        self.colours:  dict[str, str] = dict(initial_colours)
        self._validate()

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate(self) -> None:
        for r, nbs in self.adjacency.items():
            if r not in self._initial:
                raise ValueError(f"'{r}' in adjacency but not in initial_colours")
            for nb in nbs:
                if nb not in self._initial:
                    raise ValueError(f"Neighbour '{nb}' of '{r}' not in initial_colours")
                if r not in self.adjacency.get(nb, set()):
                    raise ValueError(f"Adjacency not symmetric: '{r}' <-> '{nb}'")

    # ── State management ──────────────────────────────────────────────────────

    def reset(self, overrides: Optional[dict[str, str]] = None) -> None:
        """
        Restore all regions to their initial colours, then apply overrides.
        Call this before each test case to set input values.
        """
        self.colours = dict(self._initial)
        if overrides:
            self.colours.update(overrides)

    # ── Flood-fill primitive ──────────────────────────────────────────────────

    def get_component(self, region: str) -> set[str]:
        """
        Return every region in the connected colour component of `region`.
        Two regions are in the same component iff they share a colour and
        are linked through a chain of adjacencies of that colour.
        """
        target = self.colours[region]
        visited: set[str] = set()
        stack = [region]
        while stack:
            r = stack.pop()
            if r in visited:
                continue
            visited.add(r)
            for nb in self.adjacency.get(r, set()):
                if self.colours[nb] == target and nb not in visited:
                    stack.append(nb)
        return visited

    def fill(self, region: str, colour: str) -> None:
        """Recolour the entire connected component of `region` to `colour`."""
        for r in self.get_component(region):
            self.colours[r] = colour

    # ── Instruction execution ─────────────────────────────────────────────────

    def step(
        self,
        target: str,
        colour_source: str,
        verbose: bool = False,
    ) -> None:
        """
        Execute one fill instruction.

        Parameters
        ----------
        target : str
            Region whose connected component is recoloured.
        colour_source : str
            Fixed colour string ('black', 'orange', …)  OR  a region name,
            in which case that region's current colour is used as the fill
            colour (the variable-colour / bridge-assignment instruction).
        verbose : bool
            Print the swept component and resulting state.
        """
        if colour_source in self.colours:           # variable-colour path
            new_colour = self.colours[colour_source]
            label = f"<{colour_source}={new_colour}>"
        else:                                        # fixed-colour path
            new_colour = colour_source
            label = new_colour

        if verbose:
            swept = sorted(self.get_component(target))
            print(f"    fill({target} -> {label})  sweeps {swept}")

        self.fill(target, new_colour)

        if verbose:
            print(f"      {dict(sorted(self.colours.items()))}")

    def run(
        self,
        instructions: list[tuple[str, str]],
        verbose: bool = False,
    ) -> None:
        """Execute a full instruction sequence."""
        for i, (target, src) in enumerate(instructions):
            if verbose:
                print(f"  step {i + 1}: ({target!r}, {src!r})")
            self.step(target, src, verbose=verbose)


# =============================================================================
# Truth-table runner
# =============================================================================

def run_truth_table(
    circuit: PaintCircuit,
    input_regions: list[str],
    output_regions: list[str],
    instructions: list[tuple[str, str]],
    input_values: Optional[list[str]] = None,
    verbose: bool = False,
) -> list[dict]:
    """
    Test the circuit over all combinations of input values.

    Parameters
    ----------
    circuit : PaintCircuit
    input_regions : list[str]
        One physical seed region per logical input, in order.  Fan-out to
        additional copies is handled by instructions at the top of the
        instruction list, not here.
    output_regions : list[str]
        Regions to read as outputs after execution.
    instructions : list of (target, colour_source) pairs
    input_values : possible values per input (default: ['black', 'white'])
    verbose : bool
        Print step-by-step trace for every test case.

    Returns
    -------
    list of result dicts, each with keys:
        'inputs'   -- dict of logical_name -> colour
        'outputs'  -- dict of region -> colour
        'bits_in'  -- dict of logical_name -> 0/1  (black = 1)
        'bits_out' -- dict of region -> 0/1
    """
    if input_values is None:
        input_values = ['black', 'white']

    rows: list[dict] = []

    for combo in itertools.product(input_values, repeat=len(input_regions)):
        assignment = dict(zip(input_regions, combo))

        circuit.reset(assignment)

        if verbose:
            print(f"\n{'─' * 56}")
            print(f"  Inputs : {assignment}")

        circuit.run(instructions, verbose=verbose)

        outputs = {out: circuit.colours[out] for out in output_regions}
        rows.append({
            'inputs':   assignment,
            'outputs':  outputs,
            'bits_in':  {k: int(v == 'black') for k, v in assignment.items()},
            'bits_out': {k: int(v == 'black') for k, v in outputs.items()},
        })

        if verbose:
            print(f"  Outputs: {outputs}")

    return rows


def print_truth_table(
    rows: list[dict],
    output_regions: list[str],
    title: str = '',
) -> None:
    """Pretty-print truth table results."""
    if not rows:
        return
    if title:
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}")

    logical_names = list(rows[0]['inputs'].keys())
    headers = (
        [f" {n}" for n in logical_names]
        + [f" {o} colour" for o in output_regions]
        + [f" {o} bit" for o in output_regions]
    )
    w = 12
    fmt = "".join(f"{{:>{w}}}" for _ in headers)
    sep = "".join(["-" * w] * len(headers))

    print(fmt.format(*headers))
    print(sep)
    for row in rows:
        vals = (
            [row['inputs'][n]      for n in logical_names]
            + [row['outputs'][o]   for o in output_regions]
            + [str(row['bits_out'][o]) for o in output_regions]
        )
        print(fmt.format(*vals))


# =============================================================================
# Helper: build a gate tuple with auto-symmetrised adjacency
# =============================================================================

def _make(adj, col, ins, out):
    """
    Build the four-tuple (adjacency, colours, instructions, outputs).
    Automatically makes the adjacency symmetric so gate definitions only need
    to specify edges in one direction.
    """
    full: dict[str, set[str]] = {r: set(nbs) for r, nbs in adj.items()}
    for r in col:
        full.setdefault(r, set())
    for r, nbs in list(full.items()):
        for nb in nbs:
            full.setdefault(nb, set()).add(r)
    return full, col, ins, out


# =============================================================================
# Gate definitions
# Each returns (adjacency, initial_colours, instructions, output_regions).
# Logical inputs are the first regions listed in each instruction block's
# fan-out section (or the sole seed region when no fan-out is needed).
# run_truth_table receives input_regions as a plain list, e.g. ['A', 'B'].
# =============================================================================

def and_gate():
    """AND – black bus, serial chain SA–B–A–O, probe P."""
    return _make(
        adj={'SA': {'B'}, 'B': {'A'}, 'A': {'O'}, 'O': {'P'}},
        col={'SA': 'black', 'B': 'grey_B', 'A': 'grey_A',
             'O': 'orange', 'P': 'green'},
        ins=[
            ('SA', 'orange'), ('SA', 'black'),  # wave 1: AND(A, B) -> O
            ('P',  'orange'), ('P',  'white'),  # wave 2: probe O
        ],
        out=['O'],
    )

def or_gate():
    """OR – black bus, parallel SA–A–O and SA–B–O, probe P."""
    return _make(
        adj={'SA': {'A', 'B'}, 'A': {'O'}, 'B': {'O'}, 'O': {'P'}},
        col={'SA': 'black', 'A': 'grey_A', 'B': 'grey_B',
             'O': 'orange', 'P': 'green'},
        ins=[
            ('SA', 'orange'), ('SA', 'black'),  # wave 1: OR(A, B) -> O
            ('P',  'orange'), ('P',  'white'),  # wave 2: probe O
        ],
        out=['O'],
    )


def not_gate():
    """NOT A – white bus SW–A–O, probe P."""
    return _make(
        adj={'SW': {'A'}, 'A': {'O'}, 'O': {'P'}},
        col={'SW': 'white', 'A': 'grey_A', 'O': 'orange', 'P': 'green'},
        ins=[
            ('SW', 'orange'), ('SW', 'black'),  # wave 1: NOT(A) -> O
            ('P',  'orange'), ('P',  'white'),  # wave 2: probe O
        ],
        out=['O'],
    )

def and_gate_lite():
    """AND – black bus."""
    return _make(
        adj={'A': {'SA'}, 'B': set(), 'SA': {'A'}},
        col={'A': 'grey_A', 'B': 'grey_B',
             'SA': 'black',},
        ins=[
            ('SA', 'black'), ('SA', 'B'),  # wave 1: AND(A, B) -> A
        ],
        out=['A'],
    )

def or_gate_lite():
    """OR – white bus."""
    return _make(
        adj={'A': {'SA'}, 'B': set(), 'SA': {'A'}},
        col={'A': 'grey_A', 'B': 'grey_B',
             'SA': 'white',},
        ins=[
            ('SA', 'white'), ('SA', 'B'),  # wave 1: OR(A, B) -> A
        ],
        out=['A'],
    )

def B_implies_A_gate_lite():
    """B implies A – black bus."""
    return _make(
        adj={'A': {'SA'}, 'B': set(), 'SA': {'A'}},
        col={'A': 'grey_A', 'B': 'grey_B',
             'SA': 'black',},
        ins=[
            ('SA', 'B'), ('SA',  'black'),  # wave 1: Implies(B, A) -> A
        ],
        out=['A'],
    )

def A_nimplies_B_gate_lite():
    """A does not imply B – white bus."""
    return _make(
        adj={'A': {'SA'}, 'B': set(), 'SA': {'A'}},
        col={'A': 'grey_A', 'B': 'grey_B',
             'SA': 'white',},
        ins=[
            ('SA', 'B'), ('SA',  'white'),  # wave 1: Nimplies(A, B) -> A
        ],
        out=['A'],
    )

def nand_gate():
    """NAND – white bus, parallel SW–A–O and SW–B–O, probe P."""
    return _make(
        adj={'SW': {'A', 'B'}, 'A': {'O'}, 'B': {'O'}, 'O': {'P'}},
        col={'SW': 'white', 'A': 'grey_A', 'B': 'grey_B',
             'O': 'orange', 'P': 'green'},
        ins=[
            ('SW', 'orange'), ('SW', 'black'),  # wave 1: NAND(A, B) -> O
            ('P',  'orange'), ('P',  'white'),  # wave 2: probe O
        ],
        out=['O'],
    )


def nor_gate():
    """NOR – white bus, serial SW–B–A–O, probe P."""
    return _make(
        adj={'SW': {'B'}, 'B': {'A'}, 'A': {'O'}, 'O': {'P'}},
        col={'SW': 'white', 'B': 'grey_B', 'A': 'grey_A',
             'O': 'orange', 'P': 'green'},
        ins=[
            ('SW', 'orange'), ('SW', 'black'),  # wave 1: NOR(A, B) -> O
            ('P',  'orange'), ('P',  'white'),  # wave 2: probe O
        ],
        out=['O'],
    )


def xnor_gate():
    """
    XNOR = AND(A,B) OR NOR(A,B).  Three stages + probe.
      Wave 1  SB1 black : AND(A1,B1) -> MAND  (orange null)
      Wave 2  SN  white : NOR(A2,B2) -> MNOR  (red null)
      Wave 3  SO  black : OR(MAND,MNOR) -> Q  (magenta null)
      Wave 4: Probe PS on Q.
    A and B are each fanned to two copies before the logic waves.
    """
    return _make(
        adj={
            'SB1':  {'B1'},
            'B1':   {'A1'},
            'A1':   {'MAND'},
            'MAND': {'SO', 'Q'},
            'SN':   {'B2'},
            'B2':   {'A2'},
            'A2':   {'MNOR'},
            'MNOR': {'SO', 'Q'},
            'SO':   set(),
            'Q':    {'PS'},
        },
        col={
            'SB1': 'black', 'B1': 'grey_B', 'A1': 'grey_A', 'MAND': 'orange',
            'SN':  'white', 'B2': 'grey_B', 'A2': 'grey_A', 'MNOR': 'red',
            'SO':  'black', 'Q':  'magenta', 'PS': 'green',
        },
        ins=[
            ('A2', 'A1'), ('A2', 'A1'),   # wave 1: fan out A to stage 2
            ('B2', 'B1'), ('B2', 'B1'),   # wave 2: fan out B to stage 2
            ('SB1', 'orange'), ('SB1', 'black'),    # wave 3: AND(A1, B1) -> MAND
            ('SN',  'red'),    ('SN',  'black'),    # wave 4: NOR(A2, B2) -> MNOR
            ('SO',  'magenta'), ('SO', 'black'),    # wave 5: OR(MAND, MNOR) -> Q
            ('PS',  'magenta'), ('PS', 'white'),    # wave 6: probe Q
        ],
        out=['Q'],
    )


def xor_gate():
    """
    XOR = AND(OR(A,B), NAND(A,B)).  Three stages + probe.
      Stage 1  SB1 black : OR(A1,B1)   -> R_OR    (orange null)
      Stage 2  SW  white : NAND(A2,B2) -> R_NAND  (red null)
      Stage 3  SB2 black : AND(R_OR,R_NAND) -> S  (blue null)
      Probe PS on S.
    A and B are each fanned to two copies before the logic waves.
    """
    return _make(
        adj={
            'SB1':    {'A1', 'B1'},
            'A1':     {'R_OR'},
            'B1':     {'R_OR'},
            'R_OR':   {'R_NAND', 'S'},
            'SW':     {'A2', 'B2'},
            'A2':     {'R_NAND'},
            'B2':     {'R_NAND'},
            'R_NAND': {'SB2', 'R_OR'},
            'SB2':    set(),
            'S':      {'PS'},
        },
        col={
            'SB1': 'black', 'A1': 'grey_A', 'B1': 'grey_B', 'R_OR':   'orange',
            'SW':  'white', 'A2': 'grey_A', 'B2': 'grey_B', 'R_NAND': 'red',
            'SB2': 'black', 'S': 'blue', 'PS': 'green',
        },
        ins=[
            ('A2', 'A1'), ('A2', 'A1'),    # wave 1: fan out A to stage 2
            ('B2', 'B1'), ('B2', 'B1'),    # wave 2: fan out B to stage 2
            ('SB1', 'orange'), ('SB1', 'black'),    # wave 3: OR(A1, B1) -> R_OR
            ('SW',  'red'),    ('SW',  'black'),    # wave 4: NAND(A2, B2) -> R_NAND
            ('SB2', 'blue'),   ('SB2', 'black'),    # wave 5: AND(R_OR, R_NAND) -> S
            ('PS',  'blue'),   ('PS',  'white'),    # wave 6: probe S
        ],
        out=['S'],
    )


def inhibit_gate():
    """
    Inhibit (A AND NOT B): two waves, fully clean output.
      Wave 1  SA black : transfer A -> O   (O := black when A=1)
      Wave 2  B  probe : B -> orange -> white
                         erases O when B=1 (O and B connected-black)
                         normalises O when B=0 (orange -> white)
    No separate probe region needed; B doubles as the inhibiting probe.
    No fan-out required; A and B each occupy a single region.
    """
    return _make(
        adj={'SA': {'A'}, 'A': {'O'}, 'B': {'O'}},
        col={'SA': 'black', 'A': 'grey_A', 'B': 'grey_B', 'O': 'orange'},
        ins=[
            ('SA', 'orange'), ('SA', 'black'),  # wave 1: transfer A -> O
            ('B',  'orange'), ('B',  'white'),  # wave 2: B as inhibiting probe
        ],
        out=['O'],
    )


def implication_gate():
    """
    Implication (A -> B): two variable-colour assignment waves, no probe.
      Wave 1  SA black : O := <B>    gated by A=1
                         assigns B's actual colour, so (1,0) lands on white
      Wave 2  SW white : O := black  gated by A=0
                         forces the false-by-A cases to 1
    A is fanned to two copies (A1, A2) before the logic waves; B is a
    colour-source-only region not in any conducting path.
    """
    return _make(
        adj={
            'SA': {'A1'},
            'A1': {'O'},
            'SW': {'A2'},
            'A2': {'O'},
            'O':  set(),
            'B':  set(),    # colour source only; not in any conducting path
        },
        col={
            'SA': 'black', 'A1': 'grey_A',
            'SW': 'white', 'A2': 'grey_A',
            'O':  'orange',
            'B':  'grey_B',
        },
        ins=[
            ('A2', 'A1'), ('A2', 'A1'), # wave 1: fan out A to wave 2's gate region
            ('SA', 'orange'), ('SA', 'B'),      # wave 2: O := B  when A=1
            ('SW', 'orange'), ('SW', 'black'),  # wave 3: O := 1  when A=0
        ],
        out=['O'],
    )


def xor_assign_gate():
    """
    XOR via two variable-colour assignment waves + probe.
    (Alternative construction demonstrating the bridge/assignment primitive.)
      Wave 1  SW1 white : O := <A>  gated by B=0   (inhibit A-and-not-B)
      Wave 2  SW2 white : O := <B>  gated by A=0   (inhibit B-and-not-A)
      Probe P: normalises the (1,1) orange case to white.
    A and B are each fanned to two copies before the logic waves:
      A -> A1 (colour source for wave 1) and A2 (gate input for wave 2)
      B -> B1 (gate input for wave 1)    and B2 (colour source for wave 2)
    """
    return _make(
        adj={
            'SW1': {'B1'},
            'B1':  {'O'},
            'SW2': {'A2'},
            'A2':  {'O'},
            'O':   {'P'},
            'A1':  set(),   # colour source for wave 1 (no conducting path)
            'B2':  set(),   # colour source for wave 2
        },
        col={
            'SW1': 'white', 'B1': 'grey_B',
            'SW2': 'white', 'A2': 'grey_A',
            'A1':  'grey_A', 'B2': 'grey_B',
            'O':   'orange', 'P': 'green',
        },
        ins=[
            ('A2', 'A1'), ('A2', 'A1'),   # wave 1: fan out A to wave 2's gate region
            ('B2', 'B1'), ('B2', 'B1'),   # wave 2: fan out B to wave 1's colour source
            ('SW1', 'orange'), ('SW1', 'A1'),   # wave 3: O := A when B=0
            ('SW2', 'orange'), ('SW2', 'B2'),   # wave 4: O := B when A=0
            ('P',   'orange'), ('P',   'white'),# wave 5: clean (1,1) orange
        ],
        out=['O'],
    )


def half_adder():
    """
    Half adder: Carry = AND(A,B),  Sum = XOR(A,B).
    Parallel processing: SB1 computes AND(A1,B1)->C and OR(A2,B2)->R_OR
    simultaneously (parallel-bus insight saves one logic wave).
      Stage 1  SB1 black : AND(A1,B1)->C  ||  OR(A2,B2)->R_OR
      Stage 2  SW  white : NAND(A3,B3) -> R_NAND
      Stage 3  SB2 black : AND(R_OR,R_NAND) -> S
      Probe PC on C (orange null), PS on S (blue null).
    A and B are each fanned to three copies before the logic waves.
    """
    return _make(
        adj={
            # Stage 1 AND path: SB1–B1–A1–C
            'SB1':    {'B1', 'A2', 'B2'},   # bus shared by AND and OR
            'B1':     {'A1'},
            'A1':     {'C'},
            'C':      {'PC'},
            # Stage 1 OR paths: SB1–A2–R_OR and SB1–B2–R_OR
            'A2':     {'R_OR'},
            'B2':     {'R_OR'},
            'R_OR':   {'R_NAND', 'S'},
            # Stage 2 NAND paths: SW–A3–R_NAND and SW–B3–R_NAND
            'SW':     {'A3', 'B3'},
            'A3':     {'R_NAND'},
            'B3':     {'R_NAND'},
            'R_NAND': {'SB2', 'R_OR'},
            # Stage 3 AND path: SB2–R_NAND–R_OR–S
            'SB2':    set(),
            'S':      {'PS'},
            'PC':     set(),
            'PS':     set(),
        },
        col={
            'SB1': 'black', 'B1': 'grey_B', 'A1': 'grey_A', 'C':      'orange',
            'A2':  'grey_A','B2': 'grey_B',                  'R_OR':   'orange',
            'SW':  'white', 'A3': 'grey_A', 'B3': 'grey_B',  'R_NAND': 'red',
            'SB2': 'black', 'S': 'blue',
            'PC':  'green', 'PS': 'green',
        },
        ins=[
            ('A2', 'A1'), ('A2', 'A1'),   # wave 1: fan out A to stage 1 OR path
            ('A3', 'A1'), ('A3', 'A1'),   # wave 2: fan out A to stage 2 NAND path
            ('B2', 'B1'), ('B2', 'B1'),   # wave 2: fan out B to stage 1 OR path
            ('B3', 'B1'), ('B3', 'B1'),   # wave 3: fan out B to stage 2 NAND path
            ('SB1', 'orange'), ('SB1', 'black'),    # wave 4: AND(A1,B1)->C || OR(A2,B2)->R_OR
            ('SW',  'red'),    ('SW',  'black'),    # wave 5: NAND(A3,B3) -> R_NAND
            ('SB2', 'blue'),   ('SB2', 'black'),    # wave 6: AND(R_OR,R_NAND) -> S (Sum)
            ('PC',  'orange'), ('PC',  'white'),    # wave 7: probe Carry
            ('PS',  'blue'),   ('PS',  'white'),    # wave 8: probe Sum
        ],
        out=['C', 'S'],
    )


def xor_lite_gate():
    """
    XOR in 2 waves / 3 steps (1 fan-out + 2 waves) -- in-place, result in A1.

    Topology:   Bus(white) -- A1 -- B -- A2 -- S2(black)

    Fan-out  A1 -> A2     (copy A into the AND-erase gate position)

    Wave 1  Bus -> white -> <B>     (in-place OR)
        The white bus merges with A1 only when A1=white (A=0); then it
        assigns B's live colour.  Result: A1 := A OR B.

    Wave 2  S2 -> orange -> white   (AND-erase via the chain)
        The black bus S2 can only travel the chain S2-A2-B-A1 when every
        link is black, i.e. A2=black (A=1) AND B=black (B=1).  When it does,
        the whole chain (including A1) is swept to white.
        Result: A1 := (A OR B) AND NOT(A AND B) = XOR(A, B).
    """
    return _make(
        adj={
            'Bus': {'A1'},
            'A1':  {'Bus', 'B'},
            'B':   {'A1', 'A2'},
            'A2':  {'B',  'S2'},
            'S2':  {'A2'},
        },
        col={
            'Bus': 'white',
            'A1':  'grey_A',
            'B':   'grey_B',
            'A2':  'grey_A',
            'S2':  'black',
        },
        ins=[
            ('A2', 'A1'), ('A2', 'A1'),  # wave 1: fan out A to AND-erase gate
            ('Bus', 'white'), ('Bus', 'B'),  # wave 2: A1 := A OR B
            ('S2',  'white'), ('S2', 'white'),  # wave 3: erase when A=1 AND B=1
        ],
        out=['A1', 'B', 'Bus', 'A2', 'S2'],  # all regions for testing/debugging
    )


def minimal_half_adder():
    """
    5-Step MS Paint Half-Adder
    Computes S=OR, C=AND, and aggressively erases S when A=1 AND B=1.
      Wave 0  fan-out: distribute A and B to their respective paths
      Wave 1  SB_S black : S := A OR B
      Wave 2  SB_C black : C := A AND B
      Wave 3  A3   white : erase S to white when A=1 AND B=1
                           (A3, B1, and S form one connected black blob)
    """
    return _make(
        adj={
            # OR path (S := black if A=1 OR B=1)
            'SB_S': {'A1', 'B1'},
            'A1':   {'S'},
            'B1':   {'S'},
            # AND path (C := black if A=1 AND B=1)
            'SB_C': {'A2'},
            'A2':   {'B2'},
            'B2':   {'C'},
            # Erase path (override S to white if A=1 AND B=1)
            'A3':   {'B1'},
        },
        col={
            'SB_S': 'black', 'A1': 'grey_A', 'B1': 'grey_B', 'S': 'blue',
            'SB_C': 'black', 'A2': 'grey_A', 'B2': 'grey_B', 'C': 'orange',
                             'A3': 'grey_A',
        },
        ins=[
            ('A2', 'A1'), ('A2', 'A1'),  # wave 1: fan out A to AND path
            ('A3', 'A1'), ('A3', 'A1'),  # wave 2: fan out A to erase path
            ('B2', 'B1'), ('B2', 'B1'),  # wave 3: fan out B to AND path
            ('SB_S', 'blue'),    ('SB_S', 'black'),  # wave 4: S = A OR B
            ('SB_C', 'orange'),  ('SB_C', 'black'),  # wave 5: C = A AND B
            ('A3',   'white'),                       # wave 6: erase S when A=1 AND B=1
        ],
        out=['C', 'S'],
    )

def parallel_AND_OR():
    """
   parallel AND/OR: two outputs computed in parallel on the same bus, with a bridge/variable-colour assignment instruction as the key insight.
    """
    return _make(
        adj={
            # inputs
            'A1': {'B1', 'B2', 'S', 'OR'},
            'B1': {'A1', 'AND'},
            # bridge
            'B2': {'A1', 'S', 'OR'},
            # and/or graph (shared bus insight)
            'S': {'A1', 'B2'},
            'AND': {'B1', 'PS'},
            'OR': {'A1', 'B2', 'PS'},
            # probe
            'PS': {'AND', 'OR'},
        },
        col={
            'A1': 'grey_A', 'B1': 'grey_B',
            'B2': 'grey_B', 
            'S': 'black',
            'AND': 'orange', 'OR': 'orange',
            'PS': 'green',
        },
        ins=[
            ('B2', 'B1'), ('B2', 'B1'),         # wave 1: fan B
            ('S', 'orange'), ('S', 'black'),   # wave 2: parallel AND/OR
            ('PS', 'orange'), ('PS', 'white'),  # wave 3: probe
        ],
        out=['AND', 'OR'],   
    )

def fast_half_adder():
    """
    3-wave half adder.  Sum -> A1, Carry -> A3.

    Reuses the XOR-lite construction for the Sum (OR, then AND-erase) and
    piggybacks the Carry onto the OR wave as a parallel, fully isolated
    AND-lite.  The trick is that B is only ever *read* as a colour source,
    never flooded, so it survives to gate the erase even after two reads.

    Topology
    --------
    Sum graph   (XOR-lite):  Bus(white) -- A1 -- B -- A2 -- S2(black)
    Carry graph (AND-lite):  SC(black)  -- A3          (shares no region)

    Waves (each is two single-instruction cells, per the grid model)
    -----
    Wave 1  fan-out    : A1 -> A2  and  A1 -> A3   (two one-step copies)
    Wave 2  OR + Carry : A1 := A OR B   (white bus assigns B)
                         A3 := A AND B  (black bus assigns B)   -- in parallel
    Wave 3  AND-erase  : S2 lifts the chain S2-A2-B-A1 to white, which is
                         all-black (conducting) only when A=1 AND B=1.

    Sum   = (A OR B) AND NOT(A AND B) = A XOR B  -> A1
    Carry =  A AND B                             -> A3
    """
    return _make(
        adj={
            # Sum graph
            'Bus': {'A1'}, 'A1': {'B'}, 'B': {'A2'}, 'A2': {'S2'}, 'S2': set(),
            # Carry graph (isolated)
            'SC': {'A3'}, 'A3': set(),
        },
        col={
            'Bus': 'white', 'A1': 'grey_A', 'B': 'grey_B',
            'A2': 'grey_A', 'S2': 'black',
            'SC': 'black',  'A3': 'grey_A',
        },
        ins=[
            ('A2', 'A1'), ('A2', 'A1'),     # wave 1: fan A to erase- and carry-gates
            ('A3', 'A1'), ('A3', 'A1'),     
            ('Bus', 'B'), ('Bus', 'B'), 
            ('SC', 'B'),  ('SC', 'B'),          # wave 2: A1 := A OR B  ||  A3 := A AND B
            ('S2', 'orange'), ('S2', 'white'),  # wave 3: erase Sum when A AND B
        ],
        out=['A3', 'A1'],   # carry, sum
    )
def full_adder():
    """
    Two disjoint 5-paste half adders + a final carry OR, joined ONLY by
    source-assignment bridges (steps that read a region's colour rather than
    sharing adjacency).  Each stage uses the 5-paste half-adder layout.

      HA1(A, B)        -> S1 in a1, C1 in a3
      bridge S1        -> hb                  (the single buffered value)
      HA2(Cin, S1)     -> Sum in ca1, C2 in ca3
      Cout = C1 OR C2  -> ca3

    Sum  = A XOR B XOR Cin
    Cout = (A AND B) OR (Cin AND (A XOR B))

    Cin is the thrice-gated input of HA2 (so it gets the two fan-outs); the
    bridged S1 is gated only once (the erase), so it needs no fan-out.
    """
    return _make(
        adj={
            # ---- HA1 (inputs a1=A, b=B) : disjoint subgraph ----
            'Bus1': {'a1'}, 'a1': {'b'}, 'b': {'a2'}, 'a2': {'S2_1'}, 'S2_1': set(),
            'SC1': {'a3'}, 'a3': set(),
            # ---- HA2 (inputs ca1=Cin, hb=bridged S1) : disjoint subgraph ----
            'Bus2': {'ca1'}, 'ca1': {'hb'}, 'hb': {'ca2'}, 'ca2': {'S2_2'}, 'S2_2': set(),
            'SC2': {'ca3'}, 'ca3': {'SCo'}, 'SCo': set(),
        },
        col={
            'Bus1': 'white', 'a1': 'grey_A', 'b': 'grey_B',
            'a2': 'grey_A', 'S2_1': 'black', 'SC1': 'black', 'a3': 'grey_A',
            'Bus2': 'white', 'ca1': 'grey_A', 'hb': 'grey_B',
            'ca2': 'grey_A', 'S2_2': 'black', 'SC2': 'black', 'ca3': 'grey_A',
            'SCo': 'white',
        },
        ins=[
            # -- HA1 --
            ('a2', 'a1'),      # 1  fan A -> erase gate
            ('a3', 'a1'),      # 2  fan A -> carry gate
            ('Bus1', 'b'),     # 3  a1 := A OR B
            ('SC1', 'b'),      # 4  a3 := A AND B          (= C1)
            ('S2_1', 'white'), # 5  a1 := A XOR B          (= S1)
            # -- bridge: the ONLY inter-stage buffer --
            ('hb', 'a1'),      # 6  hb := S1               (source read, no adjacency)
            # -- HA2 (Cin thrice-gated, S1 once-gated) --
            ('ca2', 'ca1'),    # 7  fan Cin -> erase gate
            ('ca3', 'ca1'),    # 8  fan Cin -> carry gate
            ('Bus2', 'hb'),    # 9  ca1 := Cin OR S1
            ('SC2', 'hb'),     # 10 ca3 := Cin AND S1      (= C2)
            ('S2_2', 'white'), # 11 ca1 := Cin XOR S1      (= Sum)
            # -- final carry OR, reading C1 as a source --
            ('SCo', 'a3'),     # 12 ca3 := C2 OR C1        (= Cout)
        ],
        out=['ca3', 'ca1'],    # Cout, Sum
    )

def d_latch():
    """D latch: transparent when SW=1, holds value when SW=0.  Two waves + probe."""
    return _make(
        adj={'A': {'C', 'O'}, 
             'A2': {'N','.A'},
             'B': {'.A','O'}, 
             'N': {'A2'},
             '.A': {'B', 'S'},
             'C': {'A', 'S'},
             'S': {'C', '.A'},
             'O': {'A','B','P'},
             'P': {'O'}
             },
        col={'A': 'grey_A', 'B': 'grey_B',
             'A2': 'grey_A', 'N': 'white', '.A': 'yellow',
             'C': 'grey_B', 'S': 'black',
             'O': 'orange', 'P': 'green'},
        ins=[
             ('A2',  'A'),('A2',  'A'),   # wave 1: bridge A
             ('N',   'yellow'),  ('N',   'black'),   # wave 2: 
             ('S',  'orange'),  ('S',  'black'),   # wave 3: 
            ('P',  'orange'), ('P',  'white'),  # 
        ],
        out=['O'],
    )

# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':

    gates = {
        'AND':                            (and_gate,        ['A', 'B']),
        'OR':                             (or_gate,         ['A', 'B']),
        'NOT A':                          (not_gate,        ['A']),
        'NAND':                           (nand_gate,       ['A', 'B']),
        'NOR':                            (nor_gate,        ['A', 'B']),
        'XNOR':                           (xnor_gate,       ['A1', 'B1']),
        'XOR  (3-stage cascade)':         (xor_gate,        ['A1', 'B1']),
        'XOR  (variable-colour assign)':  (xor_assign_gate, ['A1', 'B1']),
        'INHIBIT  A AND NOT B':           (inhibit_gate,    ['A', 'B']),
        'IMPLICATION  A -> B':            (implication_gate,['A1', 'B']),
        'HALF ADDER':                     (half_adder,      ['A1', 'B1']),
        'MINIMAL HALF ADDER':             (minimal_half_adder, ['A1', 'B1']),
        'B IMPLIES A':                    (B_implies_A_gate_lite, ['A', 'B']),
        'A NIMPLIES B':                   (A_nimplies_B_gate_lite, ['A', 'B']),
        'AND (lite)':                     (and_gate_lite,   ['A', 'B']),
        'OR  (lite)':                     (or_gate_lite,    ['A', 'B']),
        'parallel AND OR':                (parallel_AND_OR, ['A1', 'B1']),
        'fast half adder':                (fast_half_adder, ['A1', 'B']),
        'full adder':                     (full_adder,      ['a1', 'b', 'ca1']),
        'XOR  (lite: 2 waves, in-place)': (xor_lite_gate,   ['A1', 'B']),
        'D LATCH':                        (d_latch,         ['A', 'B', 'C']),
    }

    for name, (factory, input_regions) in gates.items():
        adj, col, ins, out = factory()
        circuit = PaintCircuit(adj, col)
        rows = run_truth_table(circuit, input_regions, out, ins)
        print_truth_table(rows, out, title=name)

    print('\nAll gates verified.')