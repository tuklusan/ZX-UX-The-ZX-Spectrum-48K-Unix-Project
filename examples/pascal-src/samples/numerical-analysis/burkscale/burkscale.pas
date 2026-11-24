{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkscale;
var a:array[1..5] of integer; i:integer;
begin
  a[1]:=100; a[2]:=-200; a[3]:=300; a[4]:=400; a[5]:=-500;
  for i:=1 to 5 do a[i]:=2*a[i];
  writeln('scale2 x100: ',a[1],' ',a[2],' ',a[3],' ',a[4],' ',a[5]);
  for i:=2 to 4 do a[i]:=-a[i] div 2;
  writeln('scale tail -0.5 x100: ',a[1],' ',a[2],' ',a[3],' ',a[4],' ',a[5]);
  sleep(100);
end.
