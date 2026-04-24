export interface AppLocation {
  latitude: number;
  longitude: number;
  addressLabel?: string;
}

export interface LocationMapMarker extends AppLocation {
  title?: string;
}

export interface LocationPickerDialogData {
  title?: string;
  initialLocation?: AppLocation | null;
}

export interface LocationSelectionResult {
  location: AppLocation;
  googleMapsUrl: string;
}