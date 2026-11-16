{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkl2;
var a:array[1..5] of integer; i,s,r:integer;
begin
  a[1]:=3; a[2]:=4; a[3]:=0; a[4]:=0; a[5]:=0;
  s:=0; for i:=1 to 5 do s:=s+a[i]*a[i];
  r:=0; while (r+1)*(r+1)<=s do r:=r+1;
  writeln('L2=',r);
  s:=0; for i:=2 to 5 do s:=s+a[i]*a[i];
  r:=0; while (r+1)*(r+1)<=s do r:=r+1;
  writeln('L2 tail=',r);
  s:=9; r:=0; while (r+1)*(r+1)<=s do r:=r+1;
  writeln('sqrt9=',r);
  s:=2; r:=0; while (r+1)*(r+1)<=s do r:=r+1;
  writeln('floor sqrt2=',r);
  sleep(100);
end.
