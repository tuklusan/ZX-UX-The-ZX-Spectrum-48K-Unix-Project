{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkvec;
var a:array[1..5] of integer; i,j,t,s:integer;
begin
  for i:=1 to 5 do a[i]:=i+10;
  for i:=1 to 2 do begin j:=6-i; t:=a[i]; a[i]:=a[j]; a[j]:=t end;
  writeln('reverse: ',a[1],' ',a[3],' ',a[5]);
  s:=0; for i:=1 to 5 do s:=s+a[i]; writeln('sum=',s);
  sleep(100);
end.
