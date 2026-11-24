{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkrsrt;
var a:array[1..5] of integer; i,j,n,t:integer;
begin
  a[1]:=300; a[2]:=-100; a[3]:=400; a[4]:=200; a[5]:=0;
  n:=3;
  for i:=1 to n-1 do
    for j:=2 to n-i+1 do
      if a[j]>a[j+1] then begin t:=a[j]; a[j]:=a[j+1]; a[j+1]:=t end;
  writeln('sort tail3 x100: ',a[1],' ',a[2],' ',a[3],' ',a[4],' ',a[5]);
  n:=5;
  for i:=1 to n-1 do
    for j:=1 to n-i do
      if a[j]>a[j+1] then begin t:=a[j]; a[j]:=a[j+1]; a[j+1]:=t end;
  writeln('sort5 x100: ',a[1],' ',a[2],' ',a[3],' ',a[4],' ',a[5]);
  sleep(100);
end.
