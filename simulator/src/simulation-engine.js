const winston = require("winston")
const EventEmitter = require("events")

const logger = winston.createLogger({
  level: "info",
  format: winston.format.simple(),
  transports: [new winston.transports.Console()],
})

class Train {
  constructor(data) {
    this.id = data.train_id
    this.type = data.train_type || "passenger"
    this.priority = data.priority || 3
    this.route = data.route || []
    this.currentStationIndex = 0
    this.currentStation = this.route[0]
    this.currentTrack = null
    this.status = "scheduled" // scheduled, running, delayed, stopped, completed
    this.speed = 0 // km/h
    this.maxSpeed = this.getMaxSpeedForType()
    this.delay = 0 // minutes
    this.position = 0 // position along current track (0-1)
    this.scheduledDeparture = new Date(data.scheduled_departure)
    this.scheduledArrival = new Date(data.scheduled_arrival)
    this.actualDeparture = null
    this.actualArrival = null
    this.distanceTraveled = 0
    this.fuelConsumption = 0
    this.passengerCount = data.passenger_count || this.getDefaultPassengerCount()
    this.incidents = []
  }

  getMaxSpeedForType() {
    const speedMap = {
      express: 130,
      passenger: 100,
      freight: 80,
      suburban: 90,
    }
    return speedMap[this.type] || 100
  }

  getDefaultPassengerCount() {
    const passengerMap = {
      express: 800,
      passenger: 1200,
      freight: 0,
      suburban: 1500,
    }
    return passengerMap[this.type] || 0
  }

  getCurrentSegment() {
    if (this.currentStationIndex >= this.route.length - 1) {
      return null
    }
    return `${this.route[this.currentStationIndex]}-${this.route[this.currentStationIndex + 1]}`
  }

  getNextStation() {
    if (this.currentStationIndex >= this.route.length - 1) {
      return null
    }
    return this.route[this.currentStationIndex + 1]
  }

  updatePosition(timeStepSeconds, trackDistance = 50) {
    if (this.status !== "running") return

    // Calculate distance traveled in this time step
    const distanceKm = (this.speed * timeStepSeconds) / 3600 // Convert to km
    this.distanceTraveled += distanceKm

    // Update position along current track
    this.position += distanceKm / trackDistance

    // Update fuel consumption (simplified)
    this.fuelConsumption += distanceKm * this.getFuelConsumptionRate()

    // Check if reached next station
    if (this.position >= 1.0) {
      this.arriveAtNextStation()
    }
  }

  getFuelConsumptionRate() {
    // Liters per km (simplified calculation)
    const baseRate = {
      express: 3.5,
      passenger: 4.0,
      freight: 6.0,
      suburban: 3.0,
    }
    return baseRate[this.type] || 4.0
  }

  arriveAtNextStation() {
    this.currentStationIndex++
    this.position = 0

    if (this.currentStationIndex >= this.route.length) {
      this.status = "completed"
      this.actualArrival = new Date()
      this.currentStation = this.route[this.route.length - 1]
    } else {
      this.currentStation = this.route[this.currentStationIndex]
      // Stop at station for a brief period
      this.status = "stopped"
      setTimeout(() => {
        if (this.status === "stopped") {
          this.status = "running"
        }
      }, this.getStopDuration() * 1000)
    }
  }

  getStopDuration() {
    // Stop duration in seconds based on train type
    const stopDurations = {
      express: 120, // 2 minutes
      passenger: 180, // 3 minutes
      freight: 300, // 5 minutes
      suburban: 60, // 1 minute
    }
    return stopDurations[this.type] || 120
  }

  applyIncident(incident) {
    this.incidents.push(incident)

    switch (incident.type) {
      case "signal_failure":
        this.speed = Math.min(this.speed, 20) // Reduce to 20 km/h
        break
      case "track_maintenance":
        this.status = "stopped"
        this.delay += incident.delay_minutes || 15
        break
      case "weather":
        this.speed = this.speed * 0.7 // 30% speed reduction
        break
      case "equipment_failure":
        this.status = "stopped"
        this.delay += incident.delay_minutes || 30
        break
      case "passenger_emergency":
        this.status = "stopped"
        this.delay += incident.delay_minutes || 10
        break
    }
  }

  removeIncident(incident) {
    this.incidents = this.incidents.filter((i) => i.id !== incident.id)

    // Restore normal operations if no more incidents
    if (this.incidents.length === 0) {
      this.speed = this.maxSpeed
      if (this.status === "stopped" && this.currentStationIndex < this.route.length - 1) {
        this.status = "running"
      }
    }
  }

  getStatus() {
    return {
      id: this.id,
      type: this.type,
      priority: this.priority,
      currentStation: this.currentStation,
      currentTrack: this.getCurrentSegment(),
      status: this.status,
      speed: this.speed,
      delay: this.delay,
      position: this.position,
      distanceTraveled: this.distanceTraveled,
      fuelConsumption: this.fuelConsumption,
      passengerCount: this.passengerCount,
      activeIncidents: this.incidents.length,
      routeProgress: `${this.currentStationIndex}/${this.route.length - 1}`,
    }
  }
}

class Track {
  constructor(data) {
    this.id = data.segment_id
    this.fromStation = data.from_station
    this.toStation = data.to_station
    this.distance = data.distance_km || 50
    this.maxSpeed = data.max_speed_kmh || 100
    this.capacity = data.capacity || 1
    this.isElectrified = data.is_electrified !== false
    this.trackType = data.track_type || "double"
    this.occupiedBy = new Set()
    this.maintenanceWindows = []
    this.speedRestrictions = []
    this.signalStatus = "green"
  }

  canAcceptTrain(trainId) {
    return this.occupiedBy.size < this.capacity && this.signalStatus === "green"
  }

  occupyTrack(trainId) {
    if (this.canAcceptTrain(trainId)) {
      this.occupiedBy.add(trainId)
      return true
    }
    return false
  }

  releaseTrack(trainId) {
    this.occupiedBy.delete(trainId)
  }

  isOccupied() {
    return this.occupiedBy.size > 0
  }

  getOccupancyRate() {
    return this.occupiedBy.size / this.capacity
  }

  addSpeedRestriction(restriction) {
    this.speedRestrictions.push(restriction)
  }

  removeSpeedRestriction(restrictionId) {
    this.speedRestrictions = this.speedRestrictions.filter((r) => r.id !== restrictionId)
  }

  getCurrentMaxSpeed() {
    if (this.speedRestrictions.length === 0) {
      return this.maxSpeed
    }
    return Math.min(this.maxSpeed, ...this.speedRestrictions.map((r) => r.maxSpeed))
  }
}

class SimulationEngine extends EventEmitter {
  constructor() {
    super()
    this.trains = new Map()
    this.tracks = new Map()
    this.stations = new Map()
    this.events = []
    this.incidents = []
    this.currentTime = 0
    this.timeStep = 60 // seconds
    this.isRunning = false
    this.statistics = {
      totalEvents: 0,
      conflictsDetected: 0,
      delaysGenerated: 0,
      fuelConsumed: 0,
      passengersTransported: 0,
    }
  }

  async runSimulation({ scenario, timetable, incidents, duration_minutes, time_step_seconds }) {
    logger.info(`Initializing simulation: ${duration_minutes} minutes, ${time_step_seconds}s steps`)

    this.timeStep = time_step_seconds
    this.isRunning = true

    // Initialize simulation state
    this.initializeFromTimetable(timetable)
    this.initializeIncidents(incidents || [])
    this.initializeTracks()

    const totalSteps = Math.floor((duration_minutes * 60) / time_step_seconds)
    const results = {
      scenario: scenario.name,
      startTime: new Date().toISOString(),
      trainEvents: [],
      conflicts: [],
      trackUtilization: [],
      summary: {},
      completedJourneys: 0,
      statistics: {},
    }

    // Emit simulation start event
    this.emit("simulationStart", { scenario: scenario.name, totalSteps })

    // Run simulation steps
    for (let step = 0; step < totalSteps && this.isRunning; step++) {
      this.currentTime = step * time_step_seconds

      // Process time step
      const stepResults = this.processTimeStep()
      results.trainEvents.push(...stepResults.events)
      results.conflicts.push(...stepResults.conflicts)

      // Record track utilization
      if (step % 10 === 0) {
        // Every 10 steps
        results.trackUtilization.push(this.getTrackUtilization())
      }

      // Emit progress event
      if (step % Math.floor(totalSteps / 20) === 0) {
        // Every 5%
        const progress = Math.round((step / totalSteps) * 100)
        this.emit("progress", { step, totalSteps, progress })
        logger.info(`Simulation progress: ${progress}%`)
      }
    }

    // Finalize results
    results.endTime = new Date().toISOString()
    results.summary = this.generateSummary()
    results.completedJourneys = this.countCompletedJourneys()
    results.statistics = this.statistics

    // Emit simulation end event
    this.emit("simulationEnd", results)

    logger.info("Simulation completed")
    return results
  }

  initializeFromTimetable(timetable) {
    if (!timetable || !timetable.entries) return

    timetable.entries.forEach((entry) => {
      const train = new Train(entry)
      this.trains.set(train.id, train)

      // Initialize stations from routes
      train.route.forEach((stationCode) => {
        if (!this.stations.has(stationCode)) {
          this.stations.set(stationCode, {
            code: stationCode,
            name: stationCode,
            platforms: 4,
            occupiedPlatforms: new Set(),
          })
        }
      })
    })

    logger.info(`Initialized ${this.trains.size} trains and ${this.stations.size} stations`)
  }

  initializeTracks() {
    // Generate tracks between consecutive stations in routes
    const trackSegments = new Set()

    for (const train of this.trains.values()) {
      for (let i = 0; i < train.route.length - 1; i++) {
        const from = train.route[i]
        const to = train.route[i + 1]
        const segmentId = `${from}-${to}`

        if (!trackSegments.has(segmentId)) {
          trackSegments.add(segmentId)
          this.tracks.set(
            segmentId,
            new Track({
              segment_id: segmentId,
              from_station: from,
              to_station: to,
              distance_km: 50 + Math.random() * 100, // Random distance 50-150 km
              max_speed_kmh: 100 + Math.random() * 30, // Random speed 100-130 km/h
              capacity: Math.random() > 0.7 ? 2 : 1, // 30% chance of double capacity
            }),
          )
        }
      }
    }

    logger.info(`Initialized ${this.tracks.size} track segments`)
  }

  initializeIncidents(incidents) {
    this.incidents = incidents.map((incident) => ({
      ...incident,
      startTime: new Date(incident.start_time).getTime() / 1000,
      endTime: incident.end_time ? new Date(incident.end_time).getTime() / 1000 : null,
      active: false,
      affectedTrains: new Set(),
    }))

    logger.info(`Initialized ${this.incidents.length} incidents`)
  }

  processTimeStep() {
    const events = []
    const conflicts = []

    // Update train positions and states
    for (const train of this.trains.values()) {
      this.updateTrainState(train, events)
    }

    // Process incidents
    this.processIncidents(events)

    // Detect conflicts
    conflicts.push(...this.detectConflicts())

    // Update statistics
    this.updateStatistics()

    return { events, conflicts }
  }

  updateTrainState(train, events) {
    const previousStatus = train.status

    // Start trains that should depart
    if (train.status === "scheduled") {
      const scheduledDepartureTime = train.scheduledDeparture.getTime() / 1000
      if (this.currentTime >= scheduledDepartureTime) {
        train.status = "running"
        train.actualDeparture = new Date(this.currentTime * 1000)
        train.speed = train.maxSpeed * 0.8 // Start at 80% of max speed

        events.push({
          type: "departure",
          train_id: train.id,
          station: train.currentStation,
          scheduled_time: scheduledDepartureTime,
          actual_time: this.currentTime,
          delay_minutes: Math.max(0, (this.currentTime - scheduledDepartureTime) / 60),
          timestamp: new Date(this.currentTime * 1000),
        })
      }
    }

    // Update running trains
    if (train.status === "running") {
      const currentTrack = this.tracks.get(train.getCurrentSegment())
      if (currentTrack) {
        // Apply speed restrictions
        const maxAllowedSpeed = currentTrack.getCurrentMaxSpeed()
        train.speed = Math.min(train.speed, maxAllowedSpeed)

        // Update position
        train.updatePosition(this.timeStep, currentTrack.distance)

        // Check for arrivals
        if (previousStatus !== "stopped" && train.status === "stopped") {
          const nextStation = train.getNextStation()
          if (nextStation) {
            events.push({
              type: "arrival",
              train_id: train.id,
              station: nextStation,
              scheduled_time: train.scheduledArrival.getTime() / 1000,
              actual_time: this.currentTime,
              delay_minutes: train.delay,
              timestamp: new Date(this.currentTime * 1000),
            })
          }
        }
      }
    }

    // Handle completed journeys
    if (previousStatus !== "completed" && train.status === "completed") {
      events.push({
        type: "journey_completed",
        train_id: train.id,
        station: train.currentStation,
        total_delay_minutes: train.delay,
        distance_traveled: train.distanceTraveled,
        fuel_consumed: train.fuelConsumption,
        timestamp: new Date(this.currentTime * 1000),
      })
    }
  }

  processIncidents(events) {
    for (const incident of this.incidents) {
      // Activate incidents
      if (!incident.active && this.currentTime >= incident.startTime) {
        incident.active = true
        this.applyIncident(incident, events)
      }

      // Deactivate incidents
      if (incident.active && incident.endTime && this.currentTime >= incident.endTime) {
        incident.active = false
        this.removeIncident(incident, events)
      }
    }
  }

  applyIncident(incident, events) {
    const affectedTrains = this.getTrainsInArea(incident.location)

    for (const trainId of affectedTrains) {
      const train = this.trains.get(trainId)
      if (train) {
        train.applyIncident(incident)
        incident.affectedTrains.add(trainId)

        events.push({
          type: "incident_applied",
          train_id: trainId,
          incident_id: incident.id,
          incident_type: incident.type,
          location: incident.location,
          delay_minutes: incident.delay_minutes || 0,
          timestamp: new Date(this.currentTime * 1000),
        })
      }
    }

    // Apply to tracks if applicable
    if (incident.type === "track_maintenance") {
      const track = this.tracks.get(incident.location)
      if (track) {
        track.signalStatus = "red"
      }
    }

    this.statistics.delaysGenerated += incident.delay_minutes || 0
    logger.info(`Incident activated: ${incident.type} at ${incident.location}`)
  }

  removeIncident(incident, events) {
    for (const trainId of incident.affectedTrains) {
      const train = this.trains.get(trainId)
      if (train) {
        train.removeIncident(incident)

        events.push({
          type: "incident_resolved",
          train_id: trainId,
          incident_id: incident.id,
          incident_type: incident.type,
          location: incident.location,
          timestamp: new Date(this.currentTime * 1000),
        })
      }
    }

    // Restore track status
    if (incident.type === "track_maintenance") {
      const track = this.tracks.get(incident.location)
      if (track) {
        track.signalStatus = "green"
      }
    }

    incident.affectedTrains.clear()
    logger.info(`Incident resolved: ${incident.type} at ${incident.location}`)
  }

  detectConflicts() {
    const conflicts = []

    // Track occupancy conflicts
    for (const track of this.tracks.values()) {
      if (track.occupiedBy.size > track.capacity) {
        const conflictingTrains = Array.from(track.occupiedBy)

        conflicts.push({
          type: "track_overoccupancy",
          resource: track.id,
          trains: conflictingTrains,
          severity: "high",
          timestamp: new Date(this.currentTime * 1000),
          capacity: track.capacity,
          actual_occupancy: track.occupiedBy.size,
        })

        this.statistics.conflictsDetected++
      }
    }

    // Platform conflicts at stations
    for (const [stationCode, station] of this.stations) {
      const trainsAtStation = Array.from(this.trains.values()).filter(
        (train) => train.currentStation === stationCode && train.status === "stopped",
      )

      if (trainsAtStation.length > station.platforms) {
        conflicts.push({
          type: "platform_conflict",
          resource: stationCode,
          trains: trainsAtStation.map((t) => t.id),
          severity: "medium",
          timestamp: new Date(this.currentTime * 1000),
          available_platforms: station.platforms,
          trains_requiring_platforms: trainsAtStation.length,
        })
      }
    }

    return conflicts
  }

  getTrainsInArea(location) {
    const affectedTrains = []

    for (const train of this.trains.values()) {
      // Check if train is at the location or on a track connected to it
      if (
        train.currentStation === location ||
        train.getCurrentSegment()?.includes(location) ||
        train.route.includes(location)
      ) {
        affectedTrains.push(train.id)
      }
    }

    return affectedTrains
  }

  getTrackUtilization() {
    const utilization = {}

    for (const [trackId, track] of this.tracks) {
      utilization[trackId] = {
        occupancy_rate: track.getOccupancyRate(),
        occupied_by: Array.from(track.occupiedBy),
        max_speed: track.getCurrentMaxSpeed(),
        signal_status: track.signalStatus,
        timestamp: this.currentTime,
      }
    }

    return utilization
  }

  updateStatistics() {
    this.statistics.totalEvents++
    this.statistics.fuelConsumed = Array.from(this.trains.values()).reduce(
      (total, train) => total + train.fuelConsumption,
      0,
    )
    this.statistics.passengersTransported = Array.from(this.trains.values())
      .filter((train) => train.status === "completed")
      .reduce((total, train) => total + train.passengerCount, 0)
  }

  generateSummary() {
    const totalTrains = this.trains.size
    const completedTrains = Array.from(this.trains.values()).filter((t) => t.status === "completed").length
    const delayedTrains = Array.from(this.trains.values()).filter((t) => t.delay > 5).length
    const avgDelay = Array.from(this.trains.values()).reduce((sum, t) => sum + t.delay, 0) / totalTrains || 0

    const avgFuelConsumption =
      Array.from(this.trains.values()).reduce((sum, t) => sum + t.fuelConsumption, 0) / totalTrains || 0

    return {
      totalTrains,
      completedTrains,
      delayedTrains,
      onTimeTrains: totalTrains - delayedTrains,
      onTimePerformance: ((totalTrains - delayedTrains) / totalTrains) * 100 || 100,
      averageDelay: avgDelay,
      simulationDuration: this.currentTime / 60, // minutes
      totalDistance: Array.from(this.trains.values()).reduce((sum, t) => sum + t.distanceTraveled, 0),
      averageFuelConsumption: avgFuelConsumption,
      totalFuelConsumed: this.statistics.fuelConsumed,
      passengersTransported: this.statistics.passengersTransported,
      conflictsDetected: this.statistics.conflictsDetected,
    }
  }

  countCompletedJourneys() {
    return Array.from(this.trains.values()).filter((train) => train.status === "completed").length
  }

  stopSimulation() {
    this.isRunning = false
    this.emit("simulationStopped")
  }

  getTrainStatus(trainId) {
    const train = this.trains.get(trainId)
    return train ? train.getStatus() : null
  }

  getAllTrainStatuses() {
    const statuses = {}
    for (const [trainId, train] of this.trains) {
      statuses[trainId] = train.getStatus()
    }
    return statuses
  }

  getSystemStatus() {
    return {
      isRunning: this.isRunning,
      currentTime: this.currentTime,
      totalTrains: this.trains.size,
      activeTrains: Array.from(this.trains.values()).filter((t) => t.status === "running").length,
      completedTrains: Array.from(this.trains.values()).filter((t) => t.status === "completed").length,
      activeIncidents: this.incidents.filter((i) => i.active).length,
      statistics: this.statistics,
    }
  }
}

module.exports = { SimulationEngine, Train, Track }
