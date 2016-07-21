A (hopefully exhaustive) list of triples to identify systems.

Note that upgrades within an ISA are usually considered aliases, not
separate arches.

For some systems, e.g. MIPS, there are common ambiguities, which *must* be
avoided here. Debian multiarch has some guidance.

## Schema

Each triple is a yaml file that is loaded and then parsed for `import`s.

After imports are resolved, the following fields exist:

* triple: a string, the canonical name for the target. Must match the filename.
* aliases: a list of strings, other names that should be considered identical.
* variants: a list of strings, for targets that can be convinced to work with
  this target. This is typically for 32-vs-64-bit versions of a target,
  but also for big-vs-little endian, different ABIs, etc.
* variant\_flags: a string, space-separated compiler flags needed to produce
  this target if a variant is given. If a variant is *not* given, these
  must have no effect. (This might not work for nasty systems like MIPS).
  (Actually, I think it will - there just *is* no non-variant system).
* arch: a string.
* kernel: a string.
* endian: a string.
* cpp: a list of strings. This is *merged*, not replaced, when it appears in
  multiple files. The merged list may contain duplicates.
* cpp\_require: a list of strings, specifying e.g. `#include`s needed for
  macros.
* libc: a string.
* default\_char\_sign: a string, default "signed".
* short: an int, number of bits in a C short.
* int: an int, number of bits in a C int.
* long: an int, number of bits in a C long.
* long\_long: an int, number of bits in a C long\_long.
* size: an int, number of bits in a C size\_t.
* TODO ptrdiff\_t: in case it's not the same as size\_t
* ptr: an int, number of bits in a C intptr\_t.
* reg: an int, number of bits in a typical register.
* obj: a string.
* TODO fast: a list of int, number of bits in any C intN\_fast\_t.
* TODO align

## Triples and Fragments that still need to be defined

* special things like NaCl (native client) and emscripten (counts as a kernel)
* Pre-ELF formats?
* dragonflybsd
* WinCE
* or1k
* Anything else that GCC has a configuration for (see `gcc/config.gcc`).
* Lots of ancient hardware and software. Look in `config.guess` for ideas.
