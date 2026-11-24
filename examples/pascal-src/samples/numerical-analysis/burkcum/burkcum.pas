{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkcum;
var a,c:array[1..5] of integer; i,lo,hi:integer;
begin
  a[1]:=3; a[2]:=-1; a[3]:=4; a[4]:=-2; a[5]:=5;
  c[1]:=a[1]; lo:=a[1]; hi:=a[1];
  for i:=2 to 5 do begin
    c[i]:=c[i-1]+a[i];
    if a[i]<lo then lo:=a[i];
    if a[i]>hi then hi:=a[i]
  end;
  writeln('cum5: ',c[1],' ',c[3],' ',c[5], ' min=',lo,' max=',hi);
  c[1]:=a[1]; lo:=a[1]; hi:=a[1];
  for i:=2 to 3 do begin
    c[i]:=c[i-1]+a[i];
    if a[i]<lo then lo:=a[i];
    if a[i]>hi then hi:=a[i]
  end;
  writeln('cum3: ',c[3],' min=',lo,' max=',hi);
  sleep(100);
end.
