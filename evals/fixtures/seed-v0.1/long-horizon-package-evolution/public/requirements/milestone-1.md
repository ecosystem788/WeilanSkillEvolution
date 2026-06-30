# Milestone 1: manifest parsing

Implement `parse_manifest(text)`. Input is CSV with headers `parcel_id,zone,weight`. Trim fields, uppercase zones, parse weight as a positive decimal, reject missing/duplicate parcel IDs and non-positive weights, and return records sorted by parcel ID. Do not modify requirements or tests.
