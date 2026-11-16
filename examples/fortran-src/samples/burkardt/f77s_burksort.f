C     Adapted from John Burkardt i4lib/i4lib.f GNU LGPL.
C     I4VEC_SORT_INSERT_A (25 July 2010) and
C     I4VEC_SEARCH_BINARY_A (31 August 2008).
C     Upstream Git blob e0a7be6024463bc0d34ec036080d875ed66f4c31.
C     F77S port: numbered loops, fixed dummy array, 6-char names.
      PROGRAM BSORT
      INTEGER A(9),N,B,IND
      DATA A/7,1,4,3,9,2,8,5,6/
      N=9
      CALL SRTINS(N,A)
      WRITE(6,10) A(1),A(5),A(9)
      B=7
      CALL BINSRC(N,A,B,IND)
      WRITE(6,20) IND
      B=10
      CALL BINSRC(N,A,B,IND)
      WRITE(6,20) IND
   10 FORMAT(3I4)
   20 FORMAT(I4)
      CALL SLEEP(100)
      END
      SUBROUTINE SRTINS(N,A)
      INTEGER N,A(9),I,J,X
      DO 20 I=2,N
      X=A(I)
      J=I-1
   10 CONTINUE
      IF (J .GE. 1) THEN
      IF (A(J) .GT. X) THEN
      A(J+1)=A(J)
      J=J-1
      GO TO 10
      ENDIF
      ENDIF
      A(J+1)=X
   20 CONTINUE
      RETURN
      END
      SUBROUTINE BINSRC(N,A,B,IND)
      INTEGER N,A(9),B,IND,LOW,HIGH,MID
      IND=-1
      LOW=1
      HIGH=N
   30 IF (LOW .LE. HIGH) THEN
      MID=(LOW+HIGH)/2
      IF (A(MID) .EQ. B) THEN
      IND=MID
      GO TO 40
      ENDIF
      IF (A(MID) .LT. B) THEN
      LOW=MID+1
      ELSE
      HIGH=MID-1
      ENDIF
      GO TO 30
      ENDIF
   40 CONTINUE
      RETURN
      END
