{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkl1;
var a:array[1..5] of integer; i,s,v:integer;
begin
  a[1]:=-250; a[2]:=300; a[3]:=0; a[4]:=-450; a[5]:=200;
  s:=0;
  for i:=1 to 5 do begin v:=a[i]; if v<0 then v:=-v; s:=s+v end;
  writeln('L1 x100=',s);
  s:=0;
  for i:=2 to 4 do begin v:=a[i]; if v<0 then v:=-v; s:=s+v end;
  writeln('L1 tail x100=',s);
  sleep(100);
end.
