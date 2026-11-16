{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkmin;
var a:array[1..5] of integer; b:array[1..4] of integer; lo,hi,i:integer;
begin
  a[1]:=-100; a[2]:=250; a[3]:=0; a[4]:=400; a[5]:=-325;
  b[1]:=125; b[2]:=-250; b[3]:=375; b[4]:=200;
  lo:=a[1]; hi:=a[1];
  for i:=2 to 5 do begin if a[i]<lo then lo:=a[i]; if a[i]>hi then hi:=a[i] end;
  writeln('minmax A x100: ',lo,' ',hi);
  lo:=b[2]; hi:=b[2];
  for i:=3 to 4 do begin if b[i]<lo then lo:=b[i]; if b[i]>hi then hi:=b[i] end;
  writeln('minmax tail x100: ',lo,' ',hi);
  sleep(100);
end.
