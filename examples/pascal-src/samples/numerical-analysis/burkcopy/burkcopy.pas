{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkcopy;
var a,b:array[1..5] of integer; i:integer;
begin
  a[1]:=100; a[2]:=-200; a[3]:=325; a[4]:=400; a[5]:=-500;
  for i:=1 to 5 do b[i]:=0;
  for i:=1 to 3 do b[i]:=a[i+1];
  writeln('copy3 x100: ',b[1],' ',b[2],' ',b[3],' ',b[4],' ',b[5]);
  for i:=1 to 5 do b[i]:=a[i];
  writeln('copy5 x100: ',b[1],' ',b[2],' ',b[3],' ',b[4],' ',b[5]);
  sleep(100);
end.
