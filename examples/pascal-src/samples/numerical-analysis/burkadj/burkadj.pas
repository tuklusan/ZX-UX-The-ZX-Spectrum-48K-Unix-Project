{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkadj;
var a: array[1..7] of integer; i,j,t,s:integer;
begin
  for i:=1 to 7 do a[i]:=i;
  for i:=1 to 2 do begin j:=6-i; t:=a[i]; a[i]:=a[j]; a[j]:=t end;
  s:=0; for i:=1 to 5 do s:=s+a[i];
  writeln('reverse: ',a[1],' ',a[5],' sum5=',s);
  s:=0; for i:=1 to 7 do s:=s+a[i]; writeln('sum7=',s);
  sleep(100);
end.
