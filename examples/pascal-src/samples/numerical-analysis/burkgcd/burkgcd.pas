{ Adapted from the FORTRAN numerical showcase; John Burkardt GNU LGPL algorithm. This Pascal compiler supports 16-bit INTEGER, not REAL; decimal values use x100 fixed-point when needed. }
program f77s_burkgcd;
var a:array[1..5] of integer; b:array[1..4] of integer; i,n,g,x,y,t:integer;
begin
  a[1]:=84; a[2]:=30; a[3]:=-42; a[4]:=56; a[5]:=14;
  b[1]:=18; b[2]:=24; b[3]:=30; b[4]:=42;
  g:=0;
  for i:=1 to 5 do begin
    x:=g; y:=a[i]; if x<0 then x:=-x; if y<0 then y:=-y;
    while y<>0 do begin t:=x mod y; x:=y; y:=t end; g:=x
  end;
  writeln('gcd A=',g);
  g:=0;
  for i:=1 to 4 do begin
    x:=g; y:=b[i]; if x<0 then x:=-x; if y<0 then y:=-y;
    while y<>0 do begin t:=x mod y; x:=y; y:=t end; g:=x
  end;
  writeln('gcd B=',g);
  g:=0;
  for i:=3 to 5 do begin
    x:=g; y:=a[i]; if x<0 then x:=-x; if y<0 then y:=-y;
    while y<>0 do begin t:=x mod y; x:=y; y:=t end; g:=x
  end;
  writeln('gcd tail=',g);
  sleep(100);
end.
