{ Adapted from the FORTRAN numerical showcase. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program bases;
var n,q,b,d,p,value:integer;
begin
  n:=13; b:=2; value:=0; p:=1; q:=n;
  while q>0 do begin
    d:=q mod b;
    value:=value+d*p;
    q:=q div b;
    p:=p*10
  end;
  writeln('binary digits for 13: ',value);
  sleep(100);
end.
