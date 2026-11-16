{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkmean;
var a:array[1..4] of integer; b:array[1..3] of integer; i,s:integer;
begin
  for i:=1 to 4 do a[i]:=i*100;
  b[1]:=-400; b[2]:=0; b[3]:=400;
  s:=0; for i:=1 to 4 do s:=s+a[i]; writeln('mean A x100=',s div 4);
  s:=0; for i:=1 to 3 do s:=s+b[i]; writeln('mean B x100=',s div 3);
  sleep(100);
end.
