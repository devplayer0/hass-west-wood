# West Wood Club API

The West Wood Club Android app is a white-label build of **PerfectGym Go**. It
talks to PerfectGym's hosted backend. Details below were reverse-engineered from
`android-flows.mitm` (app version 1.28.3).

## Base

- **Base URL:** `https://goapi2.perfectgym.com`
- All responses are wrapped as `{ "data": ..., "errors": ... }`.
- `errors` is `null` on success.

### Common request headers

The app sends the headers below on every request, but **most are not required**.
Testing `GET /v1/Clubs/Clubs` with only an `Authorization` header (no `X-Go-*`
headers and no app `User-Agent`) returned `200` with the full response. So for an
authenticated request, only `Authorization` is needed; the `X-Go-*` headers and
the app-specific `User-Agent` can be omitted.

| Header | Value | Required? |
| --- | --- | --- |
| `Authorization` | `bearer <token>` | Yes (authenticated endpoints) |
| `Accept` | `application/json` | No |
| `Content-Type` | `application/json` | No (GET); set it for POST bodies |
| `Accept-Language` | `en` | No |
| `X-Go-App-Platform` | `Android` | No |
| `X-Go-App-Version` | `1.28.3` | No |
| `X-Go-White-Label-ID` | `7d073db5-0ef8-4d78-89ec-4a8bebaf4cbc` | No |
| `User-Agent` | `West Wood Club/1.28.3.0 (com.perfectgym.perfectgymgo2.westwoodclub; build:1028003000; Android 16)` | No |

Note: login is different — the white-label ID is passed in the request **body**
there (see below), not as a header.

---

## Login

`POST /v1/Authorize/LogInWithEmail`

Unauthenticated. Returns a bearer token used for all subsequent requests.

**Request body:**

```json
{
  "email": "user@example.com",
  "password": "<password>",
  "clientApplicationInfo": {
    "type": "whitelabel",
    "whiteLabelId": "7d073db5-0ef8-4d78-89ec-4a8bebaf4cbc"
  }
}
```

**Response:**

```json
{
  "data": {
    "token": "<uuid>_<uuid>",
    "action": "LogIn",
    "expireTime": null,
    "isEmailConfirmed": true,
    "tokenType": "bearer",
    "authorizationHeader": "bearer <token>"
  },
  "errors": null
}
```

Use `data.authorizationHeader` verbatim as the `Authorization` header on
subsequent calls (i.e. `bearer ` + `data.token`). `expireTime` was `null` in the
capture; expiry behaviour is not yet confirmed.

---

## Club list

`GET /v1/Clubs/Clubs?timestamp=0`

Authenticated. Lists all clubs for the tenant. The `timestamp=0` query param
requests the full list (the API supports incremental sync — `timestamp` is a
per-record version, see the `timestamp` field on each item).

**Response (truncated):**

```json
{
  "data": [
    {
      "companyId": 251,
      "name": "West Wood Club Clontarf",
      "description": null,
      "longitude": -6.228,
      "latitude": 53.3634,
      "address": {
        "country": "Ireland",
        "city": "Dublin",
        "postalCode": "D03 T6T3",
        "line1": "Clontarf Road, Dublin 3",
        "line2": ""
      },
      "isHidden": false,
      "qrCodeSuffixConfig": "EndsWithWindowsNewLine",
      "id": 960,
      "timestamp": 1692837739,
      "isDeleted": false
    }
  ],
  "errors": null
}
```

Key field: `id` is the club ID referenced by other endpoints (e.g.
`WhoIsInCount`). Known club IDs from the capture: 959, 960, 961, 962, 963, 964.

---

## Current members (live occupancy)

`GET /v1/Clubs/WhoIsInCount`

Authenticated. Returns the number of members currently checked in at each club —
the live occupancy count. This is the primary signal for an occupancy sensor.

**Response:**

```json
{
  "data": [
    { "count": 253, "clubId": 959 },
    { "count": 294, "clubId": 960 },
    { "count": 122, "clubId": 961 },
    { "count": 59,  "clubId": 962 },
    { "count": 96,  "clubId": 963 },
    { "count": 70,  "clubId": 964 }
  ],
  "errors": null
}
```

`clubId` maps to `id` from the club list above.

> Note: a related endpoint `GET /v1/Classes/WhoIsIn` returns the named list of
> members booked into classes (first/last name, `classId`). That is per-class
> booking data, not live building occupancy.
