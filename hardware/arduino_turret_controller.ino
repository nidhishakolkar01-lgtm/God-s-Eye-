/*
 * PROJECT TRINETRA-C2 // ARDUINO / PARTICLE ARGON TURRET DRIVER
 * Hardware:
 *  - 2x SG90 / MG996R Servos (Pan on Pin 9, Tilt on Pin 10)
 *  - 1x OV5647 IR-Cut Solenoid Control (Pin 7)
 *  - 1x HC-SR04 Ultrasonic Distance Sensor (Trig Pin 11, Echo Pin 12)
 *  - 1x LDR Ambient Light Sensor (Analog Pin A0)
 * 
 * Protocol:
 *  - Incoming Serial: "P<pan> T<tilt> C<ircut>\n"  (e.g., "P90 T45 C1\n")
 *  - Outgoing Serial: Telemetry JSON string every 500ms
 */

#include <Servo.h>

Servo panServo;
Servo tiltServo;

const int PIN_PAN_SERVO  = 9;
const int PIN_TILT_SERVO = 10;
const int PIN_IRCUT_COIL = 7;
const int PIN_TRIG       = 11;
const int PIN_ECHO       = 12;
const int PIN_LDR        = A0;

int currentPan = 90;
int currentTilt = 90;
bool irCutEngaged = true;
unsigned long lastTelemetryTime = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }

  panServo.attach(PIN_PAN_SERVO);
  tiltServo.attach(PIN_TILT_SERVO);
  pinMode(PIN_IRCUT_COIL, OUTPUT);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);

  // Initialize boresight angles
  panServo.write(currentPan);
  tiltServo.write(currentTilt);
  digitalWrite(PIN_IRCUT_COIL, HIGH); // Default Daylight IR-Cut engaged

  Serial.println("{\"status\":\"READY\",\"node\":\"TRINETRA_TURRET_NODE_V1\"}");
}

void loop() {
  // 1. Process Incoming C2 Control Packets
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) {
      parseC2Command(line);
    }
  }

  // 2. Periodic Sensor Telemetry Broadcast (2 Hz)
  unsigned long now = millis();
  if (now - lastTelemetryTime >= 500) {
    lastTelemetryTime = now;
    broadcastTelemetry();
  }
}

void parseC2Command(String cmd) {
  int pIndex = cmd.indexOf('P');
  int tIndex = cmd.indexOf('T');
  int cIndex = cmd.indexOf('C');

  if (pIndex != -1 && tIndex != -1) {
    int nextDelim = cmd.indexOf(' ', pIndex);
    if (nextDelim == -1) nextDelim = tIndex;
    int targetPan = cmd.substring(pIndex + 1, nextDelim).toInt();
    
    int cDelim = (cIndex != -1) ? cIndex : cmd.length();
    int targetTilt = cmd.substring(tIndex + 1, cDelim).toInt();

    targetPan = constrain(targetPan, 10, 170);
    targetTilt = constrain(targetTilt, 15, 165);

    panServo.write(targetPan);
    tiltServo.write(targetTilt);
    currentPan = targetPan;
    currentTilt = targetTilt;
  }

  if (cIndex != -1) {
    int ircutVal = cmd.substring(cIndex + 1).toInt();
    irCutEngaged = (ircutVal == 1);
    digitalWrite(PIN_IRCUT_COIL, irCutEngaged ? HIGH : LOW);
  }
}

void broadcastTelemetry() {
  // Measure Ultrasonic Distance
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  long duration = pulseIn(PIN_ECHO, HIGH, 25000); // 25ms timeout
  float distanceCm = (duration > 0) ? (duration * 0.034 / 2.0) : 400.0;

  // Read LDR Ambient Light
  int rawLdr = analogRead(PIN_LDR);
  float lux = map(rawLdr, 0, 1023, 0, 1000);

  // Transmit JSON Telemetry Packet
  Serial.print("{\"pan\":");
  Serial.print(currentPan);
  Serial.print(",\"tilt\":");
  Serial.print(currentTilt);
  Serial.print(",\"ircut\":");
  Serial.print(irCutEngaged ? 1 : 0);
  Serial.print(",\"ultrasonic_distance_cm\":");
  Serial.print(distanceCm, 1);
  Serial.print(",\"ambient_lux\":");
  Serial.print(lux, 1);
  Serial.println("}");
}
