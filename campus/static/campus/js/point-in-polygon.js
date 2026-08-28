// point-in-polygon.js - reusable ray-casting point-in-polygon test.
// Used to check whether the user's GPS point is inside the real campus
// boundary shape (as opposed to Location geofences, which are simple
// circles checked with haversineDistanceMeters in geofence.js).
//
// polygon: array of { lat, lng } vertices, in order (does not need to
// repeat the first point at the end - the edge back to the start is
// assumed automatically).
//
// How it works: cast an imaginary ray from the point straight out to the
// right (increasing longitude) and count how many polygon edges it
// crosses. An odd number of crossings means the point is inside; an even
// number (including zero) means it's outside.
function isPointInPolygon(lat, lng, polygon) {
    if (!polygon || polygon.length < 3) return false;

    let inside = false;

    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const xi = polygon[i].lng, yi = polygon[i].lat;
        const xj = polygon[j].lng, yj = polygon[j].lat;

        const intersects =
            (yi > lat) !== (yj > lat) &&
            (lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi);

        if (intersects) inside = !inside;
    }

    return inside;
}
