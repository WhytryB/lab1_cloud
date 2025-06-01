terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

resource "google_project_service" "apis" {
  for_each = toset([
    "iot.googleapis.com",
    "pubsub.googleapis.com",
    "cloudfunctions.googleapis.com",
    "firestore.googleapis.com",
    "container.googleapis.com",
    "cloudbuild.googleapis.com"
  ])
  
  service = each.value
  disable_on_destroy = false
}

resource "google_pubsub_topic" "telemetry" {
  name = "iot-telemetry-data"
  
  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "alerts" {
  name = "critical-alerts"
  
  depends_on = [google_project_service.apis]
}

resource "google_pubsub_subscription" "telemetry_subscription" {
  name  = "telemetry-processor"
  topic = google_pubsub_topic.telemetry.name

  ack_deadline_seconds = 30
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_topic" "dead_letter" {
  name = "dead-letter-topic"
}

resource "google_container_cluster" "iot_cluster" {
  name     = "iot-monitoring-cluster"
  location = var.region

  remove_default_node_pool = true
  initial_node_count       = 1

  depends_on = [google_project_service.apis]
}

resource "google_container_node_pool" "primary_nodes" {
  name       = "primary-node-pool"
  location   = var.region
  cluster    = google_container_cluster.iot_cluster.name
  node_count = 3

  node_config {
    preemptible  = false
    machine_type = "e2-medium"

    service_account = google_service_account.gke_service_account.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }

  autoscaling {
    min_node_count = 1
    max_node_count = 10
  }
}

resource "google_service_account" "gke_service_account" {
  account_id   = "gke-service-account"
  display_name = "GKE Service Account"
}

resource "google_cloudfunctions_function" "telemetry_processor" {
  name        = "process-telemetry"
  description = "Process IoT telemetry data"
  runtime     = "python39"

  available_memory_mb   = 256
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.function_source.name
  entry_point          = "process_telemetry"

  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = google_pubsub_topic.telemetry.name
  }

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket" "function_bucket" {
  name     = "${var.project_id}-function-source"
  location = "US"
}

resource "google_storage_bucket_object" "function_source" {
  name   = "function-source.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = "function-source.zip"
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.iot_cluster.endpoint
}

output "telemetry_topic" {
  description = "Pub/Sub topic for telemetry"
  value       = google_pubsub_topic.telemetry.name
}