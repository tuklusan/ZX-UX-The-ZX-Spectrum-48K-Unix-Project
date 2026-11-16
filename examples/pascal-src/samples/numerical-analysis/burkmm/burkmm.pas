{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkmm;
var a:array[1..4] of integer; b,c:array[1..6] of integer; i,j,k,s:integer;
begin
  a[1]:=1; a[2]:=2; a[3]:=3; a[4]:=4;
  for i:=1 to 6 do b[i]:=i;
  for j:=1 to 3 do
    for i:=1 to 2 do begin
      s:=0; for k:=1 to 2 do s:=s+a[i+2*(k-1)]*b[k+2*(j-1)];
      c[i+2*(j-1)]:=s
    end;
  writeln('matmul: ',c[1],' ',c[4],' ',c[5]);
  for i:=1 to 2 do begin
    s:=0; for k:=1 to 2 do s:=s+a[i+2*(k-1)]*b[k]; c[i]:=s
  end;
  writeln('matmul first column: ',c[1]);
  sleep(100);
end.
