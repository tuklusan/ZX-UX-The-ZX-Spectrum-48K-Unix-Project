{ Adapted from the FORTRAN numerical showcase. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program prime;
var n,i,isp:integer;
begin
  n:=11; i:=2; isp:=1;
  while (i<=n div 2) and (isp=1) do begin
    if n mod i=0 then isp:=0;
    i:=i+1
  end;
  if isp=1 then writeln('PRIME') else writeln('COMPOSITE');
  sleep(100);
end.
