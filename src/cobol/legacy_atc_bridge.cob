      * Phase 616: Legacy ATC Bridge — COBOL Data Converter
      * 기존 ATC 시스템 연동 데이터 변환기
       IDENTIFICATION DIVISION.
       PROGRAM-ID. LEGACY-ATC-BRIDGE.
       AUTHOR. SDACS-TEAM.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-DRONE-RECORD.
          05 WS-DRONE-ID          PIC X(10).
          05 WS-LATITUDE           PIC S9(3)V9(6).
          05 WS-LONGITUDE          PIC S9(3)V9(6).
          05 WS-ALTITUDE           PIC 9(5)V99.
          05 WS-SPEED              PIC 9(3)V99.
          05 WS-HEADING            PIC 9(3)V99.
          05 WS-BATTERY-PCT        PIC 9(3).
          05 WS-STATUS-CODE        PIC X(3).

       01 WS-ATC-MESSAGE.
          05 WS-MSG-TYPE           PIC X(4).
          05 WS-MSG-CALLSIGN       PIC X(8).
          05 WS-MSG-SQUAWK         PIC 9(4).
          05 WS-MSG-ALT-FL         PIC 9(3).
          05 WS-MSG-SPEED-KTS      PIC 9(3).
          05 WS-MSG-HDG            PIC 9(3).
          05 WS-MSG-STATUS         PIC X(1).

       01 WS-CONVERSION-COUNT     PIC 9(6) VALUE 0.
       01 WS-ERROR-COUNT          PIC 9(4) VALUE 0.
       01 WS-METERS-TO-FL         PIC 9V9(4) VALUE 0.0328.

       PROCEDURE DIVISION.
       MAIN-PROCESS.
           PERFORM CONVERT-DRONE-TO-ATC
           PERFORM CONVERT-ATC-TO-DRONE
           STOP RUN.

       CONVERT-DRONE-TO-ATC.
      * Convert SDACS drone record to legacy ATC format
           MOVE "SURV" TO WS-MSG-TYPE
           STRING "SD" WS-DRONE-ID(1:6)
               DELIMITED SIZE INTO WS-MSG-CALLSIGN
           COMPUTE WS-MSG-ALT-FL =
               WS-ALTITUDE * WS-METERS-TO-FL
           COMPUTE WS-MSG-SPEED-KTS =
               WS-SPEED * 1.944
           MOVE WS-HEADING TO WS-MSG-HDG
           EVALUATE WS-STATUS-CODE
               WHEN "FLY" MOVE "A" TO WS-MSG-STATUS
               WHEN "LND" MOVE "L" TO WS-MSG-STATUS
               WHEN "EMG" MOVE "E" TO WS-MSG-STATUS
               WHEN OTHER MOVE "U" TO WS-MSG-STATUS
           END-EVALUATE
           ADD 1 TO WS-CONVERSION-COUNT.

       CONVERT-ATC-TO-DRONE.
      * Convert legacy ATC message to SDACS format
           MOVE WS-MSG-CALLSIGN(3:6) TO WS-DRONE-ID
           COMPUTE WS-ALTITUDE =
               WS-MSG-ALT-FL / WS-METERS-TO-FL
           COMPUTE WS-SPEED =
               WS-MSG-SPEED-KTS / 1.944
           MOVE WS-MSG-HDG TO WS-HEADING
           EVALUATE WS-MSG-STATUS
               WHEN "A" MOVE "FLY" TO WS-STATUS-CODE
               WHEN "L" MOVE "LND" TO WS-STATUS-CODE
               WHEN "E" MOVE "EMG" TO WS-STATUS-CODE
               WHEN OTHER MOVE "UNK" TO WS-STATUS-CODE
           END-EVALUATE
           ADD 1 TO WS-CONVERSION-COUNT.
