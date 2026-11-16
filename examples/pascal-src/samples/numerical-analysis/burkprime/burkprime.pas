{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkprime;
var n,i,j,count,prime:integer;
begin
  n:=10; count:=0;
  for i:=2 to n do begin
    prime:=1; j:=2;
    while j<i do begin if i mod j=0 then prime:=0; j:=j+1 end;
    count:=count+prime
  end;
  writeln('primes <= 10: ',count);
  n:=100; count:=0;
  for i:=2 to n do begin
    prime:=1; j:=2;
    while j<i do begin if i mod j=0 then prime:=0; j:=j+1 end;
    count:=count+prime
  end;
  writeln('primes <= 100: ',count);
  sleep(100);
end.
