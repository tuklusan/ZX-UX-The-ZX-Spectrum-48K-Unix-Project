{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkdot;
var x,y:array[1..5] of integer; i,s:integer;
begin
  for i:=1 to 5 do begin x[i]:=i; y[i]:=6-i end;
  s:=0; for i:=1 to 5 do s:=s+x[i]*y[i]; writeln('dot5=',s);
  s:=0; for i:=2 to 5 do s:=s+x[i]*y[i]; writeln('dot4 tail=',s);
  sleep(100);
end.
