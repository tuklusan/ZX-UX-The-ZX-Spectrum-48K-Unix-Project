{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burksort;
var a:array[1..9] of integer; i,j,x,lo,hi,mid,found,target:integer;
begin
  a[1]:=7; a[2]:=1; a[3]:=4; a[4]:=3; a[5]:=9;
  a[6]:=2; a[7]:=8; a[8]:=5; a[9]:=6;
  for i:=2 to 9 do begin
    x:=a[i]; j:=i-1;
    while j>=1 do begin
      if a[j]>x then begin a[j+1]:=a[j]; j:=j-1 end
      else j:=0-j-1
    end;
    if j<0 then j:=0-j-1;
    a[j+1]:=x
  end;
  writeln('sorted: ',a[1],' ',a[5],' ',a[9]);
  target:=7; lo:=1; hi:=9; found:=-1;
  while lo<=hi do begin
    mid:=(lo+hi) div 2;
    if a[mid]=target then begin found:=mid; hi:=lo-1 end
    else if a[mid]<target then lo:=mid+1 else hi:=mid-1
  end;
  writeln('search7=',found);
  target:=10; lo:=1; hi:=9; found:=-1;
  while lo<=hi do begin
    mid:=(lo+hi) div 2;
    if a[mid]=target then begin found:=mid; hi:=lo-1 end
    else if a[mid]<target then lo:=mid+1 else hi:=mid-1
  end;
  writeln('search10=',found);
  sleep(100);
end.
