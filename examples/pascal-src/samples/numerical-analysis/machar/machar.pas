{ Adapted from the FORTRAN numerical showcase. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_machar;
var radix,scale,eps,n:integer;
begin
  { INTEGER-only Pascal compiler: this tests fixed-point resolution,
    not the floating-point properties of the original MACHAR program. }
  radix:=2; scale:=100; eps:=scale; n:=0;
  while eps>1 do begin eps:=eps div radix; n:=n+1 end;
  writeln('fixed-point radix=',radix);
  writeln('scale=',scale,' half-steps=',n,' final=',eps);
  sleep(100);
end.
