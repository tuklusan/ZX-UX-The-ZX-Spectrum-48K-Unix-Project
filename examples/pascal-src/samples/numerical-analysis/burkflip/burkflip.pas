{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkflip;
var a:array[1..6] of integer; i,j,k,t:integer;
begin
  for i:=1 to 6 do a[i]:=i;
  for j:=1 to 3 do begin
    k:=2*j-1; t:=a[k]; a[k]:=a[k+1]; a[k+1]:=t
  end;
  for i:=1 to 2 do begin
    t:=a[i]; a[i]:=a[i+4]; a[i+4]:=t
  end;
  writeln('flip: ',a[1],' ',a[2],' ',a[5],' ',a[6]);
  for i:=1 to 2 do begin
    t:=a[i]; a[i]:=a[i+4]; a[i+4]:=t
  end;
  for j:=1 to 3 do begin
    k:=2*j-1; t:=a[k]; a[k]:=a[k+1]; a[k+1]:=t
  end;
  writeln('restored: ',a[1],' ',a[6]);
  sleep(100);
end.
