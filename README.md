# SmokeNotes - BBQ & Smoking Session Tracker

A containerized Python Flask web application for tracking and analyzing your BBQ and smoking sessions, complete with automatic data logging from FlameBoss devices.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Getting Started](#getting-started)
  - [Environment Setup](#environment-setup)
  - [Installation](#installation)
  - [Running with Docker](#running-with-docker)
- [Usage Guide](#usage-guide)
  - [Creating Sessions](#creating-sessions)
  - [Logging Data](#logging-data)
  - [Viewing Analytics](#viewing-analytics)
- [FlameBoss MQTT Integration](#flameboss-mqtt-integration)
- [Development](#development)
  - [Project Structure](#project-structure)
  - [Workflow](#workflow)
  - [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Screenshots](#screenshots)
- [License](#license)

## 🔍 Overview

SmokeNotes is a self-hosted application designed for people who want to track, analyze, and improve their smoking sessions. Keep detailed records of cook times, temperatures, weather conditions, and notes for each smoking session to refine your techniques over time. Own your data!

## ✨ Features

- **Session Tracking**: Create, view, edit, and delete smoking sessions
- **Temperature Logging**: Record pit and meat temperatures over time
- **Weather Integration**: Track weather conditions during your cook
- **Detailed Notes**: Document your process, observations, and results
- **FlameBoss Integration**: Automatically record data from FlameBoss devices via MQTT
- **Data Visualization**: View temperature graphs and trends over time
- **Searchable History**: Quickly find past cooks for reference
- **Mobile-Friendly**: Use on your phone or tablet while at the smoker
- **Self-Hosted**: Keep all your BBQ data private and local

- **Frontend**: Flask templates with responsive design
- **Backend**: Python Flask application
- **Database**: SQLite 
- **Containers**: Docker and Docker Compose for deployment
- **SmokeNotes MQTT**: Separate service that listens for FlameBoss data and updates your session.
- **After Session Graphing** Graph your data from Flameboss using the Get the Raw Data from inside the myflameboss cook page.

## 📦 Requirements

- Docker and Docker Compose
- Python 3.9+ (for local development)
- FlameBoss smoker controller (for automatic data logging)
- MQTT credentials for your FlameBoss device (for automatic data logging)

## 🚀 Getting Started

### Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/SmokeNotes/smokenotes.git
cd smokenotes
```


2. Update the environment variables in both files:
   Note: You'll need a free openweathermap api key from
   https://openweathermap.org/

`docker-compose.yml`:
```
- OPENWEATHER_API_KEY=
- DEFAULT_ZIP_CODE=90210
```
Instructions to get your flameboss mqtt username/password
`.env.mqtt`:
```
# For help with these settings see
#https://support.flameboss.com/support/solutions/articles/14000129040-connect-to-flame-boss-cloud-mqtt-broker
- MQTT_BROKER=s4.myflameboss.com
- MQTT_PORT=1883
- MQTT_USERNAME=
- MQTT_PASSWORD=
  If you're using public cooks change /data to /open
- MQTT_TOPIC=flameboss/your_flameboss_device_id/send/data
```

### Installation

#### Running with Docker

The easiest way to get started is using Docker Compose:

```bash
# Build and start the containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

The application will be available at http://localhost:5000 (or the port specified in your docker-compose.yml)

## 📘 Usage Guide

### Creating Sessions

1. Navigate to the dashboard and click "New Session"
2. Enter basic information:
   - Name of cook
   - Meat type
   - Smoker type
   - Target temperatures

3. Start your session and begin logging data

### Logging Data

You can log data in two ways:

1. **Manual Entry**: Use the "New session" button to manually record:
   - Smoker Target Temperatur in °F
   - Meat Type
   - Meat Weight
   - Smoker Type
   - Wood Type
   

2. **Automatic Logging**: If you've set up the FlameBoss MQTT integration, data will be automatically recorded at regular intervals.

### Viewing Analytics

- View real-time graphs of your cook session when data is ingested from Flameboss MQTT
- Analyze temperature curves over time
- Compare multiple sessions to improve your technique


## 🔌 FlameBoss MQTT Integration

SmokeNotes includes an MQTT service that connects to the FlameBoss MQTT stream to automatically log cooking data:

1. Update the MQTT credentials in the docker-compose.yml
2. The MQTT service will:
   - Create a new session automatically when data is first received
   - Record pit and meat temperatures at regular intervals
   - Display real-time graphs of your cook progress

To add additional information to auto-created sessions, use the "Edit Session" button to update details like meat type, weight, and notes.


### Environment Variables

#### Application 

| Variable | Description | Default |
|----------|-------------|---------|
| OPENWEATHER_API_KEY | Optional API key for weather data| NULL |
| DEFAULT_ZIP_CODE | Your zip code to get local weather| 90210 |


#### MQTT 

| Variable | Description | Example |
|----------|-------------|---------|
| MQTT_BROKER | FlameBoss MQTT broker address | s4.myflameboss.com |
| MQTT_PORT | MQTT broker port | 1883 |
| MQTT_USERNAME | Your FlameBoss account username | T-30837|
| MQTT_PASSWORD | Your FlameBoss account password | lmi3nfjsds |
| MQTT_TOPIC | Topic to subscribe to | flameboss/device_id/send/data |


## ❓ Troubleshooting

### Common Issues

1. **MQTT connection issues**
   - Verify your FlameBoss credentials in the docker-compose variables
   - Check that your FlameBoss device is online and properly configured
   - Look at the smokenotes mqtt logs: `docker-compose logs `

2. **No data appearing in graphs**
   - Confirm that the smokenotes mqtt container is receiving data
   - Check database connectivity
   - Verify that you have an active session

3. **Docker container issues**
   - Make sure Docker is installed and running
   - Check container logs: `docker-compose logs`
   - Verify environment files are properly configured

4. **Database errors**
   - Check file permissions for the SQLite database
   - Verify database connection strings in both environment files

## 👥 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Screenshots

![image](https://github.com/user-attachments/assets/5127b81d-e63d-435b-bbb1-0a7c1a147a58)

  Add current weather to your notes with 1 click.
  ![image](https://github.com/user-attachments/assets/9574e586-f65a-44e7-a8ba-d62c8391dd3c)  

  Real time graphing locally for your cooks when using MQTT.
  ![image](https://github.com/user-attachments/assets/9789ba2a-c9a7-445e-8d67-54be660b2c69)

  Keep track of your past cooks easily.
  ![image](https://github.com/user-attachments/assets/52226fd4-df4d-4c22-b046-ade26ae7d438)




## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
