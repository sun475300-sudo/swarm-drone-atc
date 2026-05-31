       IDENTIFICATION DIVISION.
       PROGRAM-ID. ATC-BRIDGE.
      * SDACS Phase 616 -- COBOL legacy ATC bridge adapter
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 DRONE-ID         PIC X(32).
       01 DRONE-ALT        PIC 9(4)V99.
       01 DRONE-SPEED      PIC 9(3)V99.
       PROCEDURE DIVISION.
           DISPLAY "SDACS ATC BRIDGE READY".
           STOP RUN.
