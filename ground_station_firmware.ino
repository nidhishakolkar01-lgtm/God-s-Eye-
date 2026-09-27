/*
  PROJECT TRINETRA-C2 // 2.4GHz NRF24L01 GROUND STATION RF TRANSMITTER
  Target: Arduino Nano (ATmega328P)
  Features:
    - 115200 Baud High-Speed USB Serial Link with Python C2
    - Direct 2.4GHz Over-The-Air RF packet transmission
    - Solderless SPI Interface with NRF24L01
    - Visual Servoing PID Setpoint Execution (Roll, Pitch, Throttle, Yaw)
    - Auto-Takeoff, Auto-Land, and Emergency Kill-Switch Flags
*/

#include <SPI.h>

// NRF24L01 Control Pins
#define PIN_CE  9
#define PIN_CSN 10

// SPI Commands
#define NRF_R_REGISTER    0x00
#define NRF_W_REGISTER    0x20
#define NRF_R_RX_PAYLOAD  0x61
#define NRF_W_TX_PAYLOAD  0xA0
#define NRF_FLUSH_TX      0xE1
#define NRF_FLUSH_RX      0xE2
#define NRF_NOP           0xFF

// Registers
#define NRF_CONFIG        0x00
#define NRF_EN_AA         0x01
#define NRF_EN_RXADDR     0x02
#define NRF_SETUP_AW      0x03
#define NRF_SETUP_RETR    0x04
#define NRF_RF_CH         0x05
#define NRF_RF_SETUP      0x06
#define NRF_STATUS        0x07
#define NRF_TX_ADDR       0x0A
#define NRF_RX_ADDR_P0    0x0B

// Channel hopping table for Bayang / E88 2.4GHz protocol
const uint8_t rf_channels[4] = { 0x00, 0x10, 0x20, 0x30 };
uint8_t current_channel_idx = 0;

// Current Flight Setpoints [0-255], 128 = Neutral
uint8_t roll_val = 128;
uint8_t pitch_val = 128;
uint8_t throttle_val = 0;
uint8_t yaw_val = 128;
uint8_t flags_val = 0;

// RX Serial Protocol Buffer: [0xAA, Roll, Pitch, Throttle, Yaw, Flags, Checksum, 0x55]
#define SERIAL_BUF_SIZE 8
uint8_t serial_buf[SERIAL_BUF_SIZE];
uint8_t serial_idx = 0;
unsigned long last_packet_time = 0;

void nrf_write_reg(uint8_t reg, uint8_t value) {
  digitalWrite(PIN_CSN, LOW);
  SPI.transfer(NRF_W_REGISTER | (reg & 0x1F));
  SPI.transfer(value);
  digitalWrite(PIN_CSN, HIGH);
}

void nrf_write_buf(uint8_t reg, const uint8_t *buf, uint8_t len) {
  digitalWrite(PIN_CSN, LOW);
  SPI.transfer(NRF_W_REGISTER | (reg & 0x1F));
  for (uint8_t i = 0; i < len; i++) {
    SPI.transfer(buf[i]);
  }
  digitalWrite(PIN_CSN, HIGH);
}

void nrf_init() {
  pinMode(PIN_CE, OUTPUT);
  pinMode(PIN_CSN, OUTPUT);
  digitalWrite(PIN_CE, LOW);
  digitalWrite(PIN_CSN, HIGH);

  SPI.begin();
  SPI.setDataMode(SPI_MODE0);
  SPI.setBitOrder(MSBFIRST);
  SPI.setClockDivider(SPI_CLOCK_DIV4); // 4MHz SPI

  delay(50);

  // Configure NRF24 for 250kbps / 1Mbps high power transmission
  nrf_write_reg(NRF_CONFIG, 0x0E); // Power Up, TX Mode, CRC 2-byte enabled
  nrf_write_reg(NRF_EN_AA, 0x00);  // Disable auto-ack for direct multi-cast
  nrf_write_reg(NRF_EN_RXADDR, 0x01);
  nrf_write_reg(NRF_SETUP_AW, 0x03); // 5-byte address
  nrf_write_reg(NRF_SETUP_RETR, 0x00); // No retransmit
  nrf_write_reg(NRF_RF_SETUP, 0x26); // 250kbps, 0dBm max power
  nrf_write_reg(NRF_RF_CH, rf_channels[0]);

  // Set Address
  const uint8_t tx_addr[5] = { 0x66, 0x88, 0x68, 0x68, 0x68 };
  nrf_write_buf(NRF_TX_ADDR, tx_addr, 5);
}

void send_rf_packet() {
  uint8_t payload[10];
  payload[0] = 0xA5; // Standard sync
  payload[1] = roll_val;
  payload[2] = pitch_val;
  payload[3] = throttle_val;
  payload[4] = yaw_val;
  payload[5] = flags_val;
  
  // Calculate checksum
  uint8_t chk = 0;
  for (uint8_t i = 0; i < 6; i++) {
    chk ^= payload[i];
  }
  payload[6] = chk;
  payload[7] = 0x5A;

  // Hop RF channel
  current_channel_idx = (current_channel_idx + 1) % 4;
  nrf_write_reg(NRF_RF_CH, rf_channels[current_channel_idx]);

  // Flush and Write Payload
  digitalWrite(PIN_CSN, LOW);
  SPI.transfer(NRF_FLUSH_TX);
  digitalWrite(PIN_CSN, HIGH);

  digitalWrite(PIN_CSN, LOW);
  SPI.transfer(NRF_W_TX_PAYLOAD);
  for (uint8_t i = 0; i < 8; i++) {
    SPI.transfer(payload[i]);
  }
  digitalWrite(PIN_CSN, HIGH);

  // Pulse CE to transmit
  digitalWrite(PIN_CE, HIGH);
  delayMicroseconds(15);
  digitalWrite(PIN_CE, LOW);
}

void setup() {
  Serial.begin(115200);
  nrf_init();
  pinMode(13, OUTPUT);
  digitalWrite(13, HIGH);
  Serial.println("[TRINETRA-RF-BRIDGE] Ready on 115200 Baud.");
}

void loop() {
  // Read Serial Stream from Python Ground Station
  while (Serial.available() > 0) {
    uint8_t b = Serial.read();

    if (serial_idx == 0) {
      if (b == 0xAA) {
        serial_buf[serial_idx++] = b;
      }
    } else if (serial_idx < SERIAL_BUF_SIZE) {
      serial_buf[serial_idx++] = b;

      if (serial_idx == SERIAL_BUF_SIZE) {
        if (serial_buf[7] == 0x55) {
          uint8_t chk = serial_buf[1] ^ serial_buf[2] ^ serial_buf[3] ^ serial_buf[4] ^ serial_buf[5];
          if (chk == serial_buf[6]) {
            roll_val = serial_buf[1];
            pitch_val = serial_buf[2];
            throttle_val = serial_buf[3];
            yaw_val = serial_buf[4];
            flags_val = serial_buf[5];
            last_packet_time = millis();
          }
        }
        serial_idx = 0;
      }
    }
  }

  // Failsafe: If no command from Python for >1.5s, drop throttle to zero
  if (millis() - last_packet_time > 1500) {
    throttle_val = 0;
    roll_val = 128;
    pitch_val = 128;
    yaw_val = 128;
    flags_val = 0;
  }

  // Transmit 2.4GHz RF packet at ~50Hz (every 20ms)
  send_rf_packet();
  delay(20);
}
