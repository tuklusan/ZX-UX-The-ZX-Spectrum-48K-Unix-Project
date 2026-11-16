{ Adapted from the FORTRAN numerical showcase. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program factorial;
var n,i,result:integer;
begin
  n:=6; result:=1;
  for i:=1 to n do result:=result*i;
  writeln('6! = ',result);
  sleep(100);
end.
