      * Phase 616 — COBOL Legacy ATC Bridge for SDACS
      * Interfaces with legacy Air Traffic Control systems via fixed-width records

       IDENTIFICATION DIVISION.
       PROGRAM-ID. LEGACY-ATC-BRIDGE.
       AUTHOR. SDACS-TEAM.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ATC-INPUT-FILE ASSIGN TO "atc_input.dat"
               ORGANIZATION IS SEQUENTIAL.
           SELECT ATC-OUTPUT-FILE ASSIGN TO "atc_output.dat"
               ORGANIZATION IS SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD  ATC-INPUT-FILE.
       01  ATC-INPUT-RECORD.
           05  ATC-DRONE-ID       PIC X(8).
           05  ATC-POS-X          PIC 9(6)V99.
           05  ATC-POS-Y          PIC 9(6)V99.
           05  ATC-POS-Z          PIC 9(4)V99.
           05  ATC-BATTERY        PIC 9(3)V9.
           05  ATC-PHASE          PIC X(10).

       FD  ATC-OUTPUT-FILE.
       01  ATC-OUTPUT-RECORD      PIC X(80).

       WORKING-STORAGE SECTION.
       01  WS-EOF-FLAG            PIC X VALUE 'N'.
           88  WS-EOF             VALUE 'Y'.
       01  WS-RECORD-COUNT        PIC 9(6) VALUE ZERO.
       01  WS-CONFLICT-COUNT      PIC 9(4) VALUE ZERO.
       01  WS-ADVISORY-MSG        PIC X(60).

       PROCEDURE DIVISION.
       MAIN-PARA.
           OPEN INPUT ATC-INPUT-FILE
           OPEN OUTPUT ATC-OUTPUT-FILE
           PERFORM READ-RECORDS UNTIL WS-EOF
           CLOSE ATC-INPUT-FILE
           CLOSE ATC-OUTPUT-FILE
           STOP RUN.

       READ-RECORDS.
           READ ATC-INPUT-FILE
               AT END MOVE 'Y' TO WS-EOF-FLAG
               NOT AT END
                   ADD 1 TO WS-RECORD-COUNT
                   PERFORM PROCESS-RECORD
           END-READ.

       PROCESS-RECORD.
           IF ATC-BATTERY < 20.0
               ADD 1 TO WS-CONFLICT-COUNT
               MOVE SPACES TO WS-ADVISORY-MSG
               STRING "LOW BATTERY: " DELIMITED SIZE
                      ATC-DRONE-ID DELIMITED SPACE
                      INTO WS-ADVISORY-MSG
               WRITE ATC-OUTPUT-RECORD FROM WS-ADVISORY-MSG
           END-IF.
