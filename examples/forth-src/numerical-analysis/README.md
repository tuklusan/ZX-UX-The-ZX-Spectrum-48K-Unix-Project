# F83 numerical-analysis collection

These 20 programs are adapted from the supplied Forth-83 archive,
`src/examples/forth-src/numerical-analysis/original/F83_Z80_SUITE.zip`.
The source archive is excluded from `dist/`.

## Contents

- `original/F83_Z80_SUITE.zip` preserves the complete original suite.
  It includes the original `.F83` sources, `COMMON.F83`, optional `LINCORE.F83`,
  the `CPM/` line-ending copies, the included host-model tools, checksums, and
  reference outputs.  The ZIP has no generated `tools/__pycache__/`.
- The twenty lowercase `.fth` files in this directory are the rfc-target
  adaptations that `forthbuild.py` compiles.
- `F83_Z80_SUITE/reference/EXPECTED.csv` inside the ZIP contains the expected output
  lines.  `HOST_OUTPUT.TXT` is the included constrained-host-model fixture;
  `AUDIT_REPORT.TXT` records the archive's source audit and model run.

The archive reports 20/20 source audits, constrained-model runs, and
host-output comparisons. These results cover the supplied host model.
The separate `rfc` → `ras` → `rld` → `rvm` check tests the Z80 target.

## Adaptation for rfc

Each target `.fth` file contains, in order:

1. a source comment;
2. the contents of `F83_Z80_SUITE/COMMON.F83` inside the ZIP;
3. `LINCORE.F83` for `minilin`, `lupivot`, and `polyfit`;
4. the corresponding original demo source.

The support sources are concatenated because rfc is a batch compiler and does
not implement the historical interactive `INCLUDE`/`LOAD` workflow.  The
numerical algorithms and expected output tags are otherwise retained.  The
archive's CP/M copies and Python host model are not compiled as target
programs.

The demos use signed 16-bit cells and Q1000 fixed-point arithmetic.  They do
not claim required floating-point support.  They exercise static data, `D+`,
`UM/MOD`, floored `MOD`, nested loops, matrix operations, root finding,
quadrature, ODE integration, relaxation, FFT, and polynomial fitting.

## License status

The project owner confirmed ownership of these sources. The supplied archive
does not contain a separate licence file.

## Expected outputs

The expected fixture has one or more lines per program.  Output comparison is
token/value based rather than whitespace based because Forth numeric formatting
may vary.  The canonical program tags are:

```text
WHET, MACHAR, LCG, SQUARE, MINILIN, GEMM, LUPIVOT, THOMAS,
CHOLESKY, BRENT, NEWTON, BISECT, ROMBERG, SIMPSON, GAUSS,
RK4, EULER, JACOBI, FFT, POLYFIT
```

The archive's exact lines are in its `F83_Z80_SUITE/reference/EXPECTED.csv`.
