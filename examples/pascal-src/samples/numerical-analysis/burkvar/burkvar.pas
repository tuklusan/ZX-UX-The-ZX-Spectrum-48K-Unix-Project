{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkvar;
var a:array[1..5] of integer; n,i,s,avg,v,d:integer;
begin
  for i:=1 to 5 do a[i]:=i;
  n:=5; s:=0; for i:=1 to n do s:=s+a[i]; avg:=s div n;
  v:=0; for i:=1 to n do begin d:=a[i]-avg; v:=v+d*d end;
  v:=v*100 div (n-1); writeln('variance5 x100=',v);
  n:=3; s:=0; for i:=2 to 4 do s:=s+a[i]; avg:=s div n;
  v:=0; for i:=2 to 4 do begin d:=a[i]-avg; v:=v+d*d end;
  v:=v*100 div (n-1); writeln('variance3 x100=',v);
  n:=1; writeln('variance1 x100=0');
  sleep(100);
end.
