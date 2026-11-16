C     John Burkardt I4MAT_FLIP_ROWS, I4MAT_FLIP_COLS.
C     GNU LGPL, i4lib/i4lib.f, source blob e0a7be6024463bc0d34e
C     c036080d875ed66f4c31. F77S adaptation, A(2,N).
      PROGRAM BFLIP
      INTEGER A(2,3),N
      DATA A/1,2,3,4,5,6/
      N=3
      CALL FLROWS(N,A)
      CALL FLCOLS(N,A)
      WRITE(6,10) A(1,1),A(2,1),A(1,3),A(2,3)
      CALL FLCOLS(N,A)
      CALL FLROWS(N,A)
      WRITE(6,20) A(1,1),A(2,3)
   10 FORMAT(4I4)
   20 FORMAT(2I4)
      CALL SLEEP(100)
      END
      SUBROUTINE FLROWS(N,A)
      INTEGER N,A(2,N),J,T
      DO 10 J=1,N
      T=A(1,J)
      A(1,J)=A(2,J)
      A(2,J)=T
   10 CONTINUE
      RETURN
      END
      SUBROUTINE FLCOLS(N,A)
      INTEGER N,A(2,N),H,J,K,I,T
      H=N/2
      DO 20 J=1,H
      K=N+1-J
      DO 10 I=1,2
      T=A(I,J)
      A(I,J)=A(I,K)
      A(I,K)=T
   10 CONTINUE
   20 CONTINUE
      RETURN
      END
