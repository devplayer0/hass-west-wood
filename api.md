# West Wood Club API

The West Wood Club Android app is a white-label build of **PerfectGym Go**. It
talks to PerfectGym's hosted backend. Details below were reverse-engineered from
`android-flows.mitm` (app version 1.28.3).

> **Caveat:** this document was written by an AI agent from a single traffic
> capture and a decompiled APK. It reflects what was observed, not official docs —
> treat field meanings, requirements, and especially inferred behaviour as
> best-effort and verify before relying on anything.

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
subsequent calls (i.e. `bearer ` + `data.token`).

**The token most likely does not expire.** `expireTime` was `null` in the capture,
the login response carries no refresh token, and the app appears not to store any
credentials to silently re-login — it seems to just hold the one bearer token. So
treating it as long-lived is reasonable. This is an inference, not a guarantee: the backend has
`TokenExpired` / `InvalidToken` error codes, so it can still invalidate a token
server-side. Handle a `401`/`403` by obtaining a fresh token.

---

## White-label ID

`7d073db5-0ef8-4d78-89ec-4a8bebaf4cbc` identifies the West Wood **tenant**. It is
not a secret — it appears in deep-link URLs — and is **hardcoded into the app
binary** (confirmed by decompiling the APK: it is a string literal in the smali,
not in resources/assets or fetched at runtime). A different white-label brand is a
different build with a different UUID.

The app uses it three ways:

- **`X-Go-White-Label-ID` request header** on API calls (not required by the
  server, per the header table above, but the app always sends it).
- **`clientApplicationInfo.whiteLabelId`** in the login body, paired with
  `type: whitelabel`. PerfectGym Go also has a `universal` mode (the generic
  multi-tenant app) that omits the white-label ID; white-label builds pin one
  tenant via this UUID.
- **`pgg-<uuid>`** in the in-app web-flow deep links (e.g.
  `https://goapi2.perfectgym.com/contract/purchase/pgg-7d073db5-...`).

It corresponds to `companyId 251` ("West Wood Club") server-side: the UUID is the
public tenant key, `companyId` the internal numeric id (see
[Other endpoints](#other-endpoints)). `GET /v1/Companies/Companies` lists every
tenant on the platform (the universal-mode operator list).

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

---

## Other endpoints

Every other endpoint seen in the capture is catalogued below, grouped by area.
Personal data, IDs, and amounts are anonymised. Samples show a single
representative `data[]` item (the wrapper and `timestamp`/`isDeleted` fields are
omitted for brevity). "Empty in capture" means the endpoint returned `data: []`
for this account, so the item shape is unknown.

Most are `GET`, authenticated with the bearer header, and return the standard
`{ "data": [...], "errors": null }` wrapper. Many take `timestamp=0` (full list)
and some take `companyId`.

`companyId` is the PerfectGym **tenant** (the gym operator), not an individual
gym — `251` is West Wood Club (from `GET /v1/Companies/Companies`, which lists
every operator on the platform). It's effectively a constant here. An individual
gym is a `clubId` (= `id` in `Clubs/Clubs`); every record carries both.

### Opening hours

`GET /v1/Clubs/OpeningHours?companyId=251&timestamp=0`

Per-club weekly hours — one row per club per `dayOfWeekOrHoliday`. Good for an
"open now" binary sensor. `OpeningHoursExceptions` (same params) holds holiday
overrides and was empty in the capture.

```json
{
  "clubId": 959,
  "dayOfWeekOrHoliday": "Monday",
  "isClosed": false,
  "openFrom": "06:00",
  "openUntil": "23:00",
  "openTwentyFourSeven": false,
  "isOpenTwentyFourHours": false,
  "companyId": 251,
  "id": 5323
}
```

### Personal training bookings

`GET /v1/PersonalTrainings/Bookings?timestamp=0`

The account's PT sessions. `Classes/BookingsV2` (same shape, class bookings) was
empty in the capture. `instructorId` maps to `Instructors/Instructors`;
`clubId` to the club list.

```json
{
  "name": "1st Consultation",
  "startDate": "2026-04-20T08:45:00+01:00",
  "endDate": "2026-04-20T09:15:00+01:00",
  "isCanceled": false,
  "isCompleted": false,
  "instructorId": 0,
  "clubId": 962,
  "personalTrainingTypeId": 0,
  "remoteAccountId": 0,
  "companyId": 251,
  "id": 0
}
```

### Membership contract

`GET /v1/RemoteAccounts/Contracts?timestamp=0`

The account's membership contract(s). `status` (e.g. `Current`), `startDate`,
`cancelDate`, `endDate` — useful for a membership-status sensor.

```json
{
  "status": "Current",
  "startDate": "2026-04-20T00:00:00+00:00",
  "cancelDate": null,
  "endDate": null,
  "paymentPlanId": 0,
  "accountId": 0,
  "remoteAccountId": 0,
  "companyId": 251,
  "id": 0
}
```

### Upcoming charges

`GET /v1/RemoteAccounts/ContractsCharges?timestamp=0`

Scheduled membership charges — `dueDate` + `amountGross`/`toPay` (value +
`currencyIso`). Useful for a "next payment" sensor.

```json
{
  "dueDate": "2026-07-01T00:00:00+00:00",
  "amountGross": { "value": "0.0000", "currencyIso": "EUR" },
  "toPay": { "value": "0.0000", "currencyIso": "EUR" },
  "description": "<plan name> (31 days) in 2026-07",
  "type": "Membership",
  "contractId": 0,
  "accountId": 0,
  "companyId": 251,
  "id": 0
}
```

### Perfect Score

`GET /v1/PerfectScore/PerfectScore`

A single gamification points value for the account. `PerfectScoreLevels` lists the
level thresholds. `Goals/GoalsProgresses` (goal tracking) was empty in the capture.

```json
{ "data": [ { "points": 175 } ], "errors": null }
```

`GET /v1/PerfectScore/PerfectScoreLevels` — the level ladder (`type` is a colour
band) with promotion/demotion dates per level:

```json
{ "type": "Green", "points": 0, "promotionDate": "2026-04-20T00:00:00+00:00", "demotionDate": null, "id": 0 }
```

### Account & profile

`GET /v1/Accounts/Account?timestamp=0` — the signed-in user's profile (PII).

```json
{
  "email": "user@example.com",
  "isEmailConfirmed": true,
  "firstName": "<first>",
  "lastName": "<last>",
  "nickName": null,
  "birthdate": "1990-01-01",
  "phoneNumber": "<phone>",
  "gender": "Male",
  "photoUrl": null,
  "instagramUrl": null,
  "id": 0
}
```

`GET /v1/Accounts/AccountNotificationsSettings?timestamp=0` — per-channel
notification toggles (`isClubNotificationsActive`, `isBookingsNotificationsActive`,
`isClassReminderActive`, `is{Sms,Email,Push}NotificationsChannelActive`,
`minutesBeforeClassReminderConfiguration`, …).

`GET /v1/Accounts/AccountPrivacySettings?timestamp=0` — leaderboard/booking
visibility flags (`showUserClassBookings`, `showUserOnPerfectScoreLeaderboard`,
`showUserOnClubGamesLeaderboards`).

`GET /v1/Accounts/FamilyMembers?timestamp=0` — linked family members. Empty in
capture.

### Remote accounts (membership identity)

A "remote account" links the app user to a membership at a company. Most
membership endpoints key off `remoteAccountId`.

`GET /v1/RemoteAccounts/Accounts?timestamp=0`:

```json
{
  "accountId": 0,
  "companyId": 251,
  "remoteId": 0,
  "homeClubId": 962,
  "isSelected": true,
  "businessNumber": "<membership-no>",
  "id": 0
}
```

`GET /v1/RemoteAccounts/PaymentPlans?timestamp=0` — membership plan definitions
(`name`, `priceGross`, `commitmentPeriodMonths`, `paymentIntervalMonths`). Amount
redacted:

```json
{
  "name": "<plan name>",
  "priceGross": { "value": "0.0000", "currencyIso": "EUR" },
  "commitmentPeriodMonths": 24,
  "paymentIntervalMonths": 1,
  "companyId": 251,
  "id": 0
}
```

### Classes catalogue

`GET /v1/Classes/Classes?timestamp=0` — scheduled class instances (the timetable):

```json
{
  "startDate": "2026-05-26T10:45:00+01:00",
  "endDate": "2026-05-26T11:15:00+01:00",
  "attendeesCount": 0,
  "attendeesLimit": null,
  "standbyListLimit": 0,
  "isReservationRequired": true,
  "isStreamingAvailable": false,
  "clubZone": "Main gym floor",
  "instructorId": 0,
  "classTypeId": 20193,
  "clubId": 960,
  "companyId": 251,
  "id": 0
}
```

`GET /v1/Classes/ClassesTypes?timestamp=0` — class-type catalogue (`name`,
`description`, `photoUrl`, `isAvailableInMobileApp`). `classTypeId` on a class
points here.

`GET /v1/Classes/Tags?timestamp=0` — the tag vocabulary (`type`, `name`,
`photoUrl`), e.g. `Strength`, `Yoga`, `Cardio`.

`GET /v1/Classes/ClassesTypesTags?timestamp=0` — many-to-many join of `tagId` ↔
`classTypeId`.

`GET /v1/Classes/ClassesTypesRatingSummaries?timestamp=0` — aggregate `rating` +
`ratingsCount` per `classTypeId`.

`GET /v1/Classes/ClassesRatings`, `GET /v1/Classes/ClassesVisits`,
`GET /v1/Classes/Favourites` — per-account ratings, visit history, and favourited
classes. All empty in capture.

### Instructors

`GET /v1/Instructors/Instructors?timestamp=0` — instructor directory:

```json
{
  "firstName": "<first>",
  "lastName": "<last>",
  "displayName": "<name>",
  "position": "Swim",
  "sex": "Female",
  "isActive": false,
  "photoUrl": null,
  "description": null,
  "companyId": 251,
  "id": 0
}
```

`GET /v1/Instructors/InstructorsClubs?timestamp=0` — join of `instructorId` ↔
`clubId`. `GET /v1/Instructors/Favourites` — favourited instructors (empty in
capture).

`GET /v1/PersonalTrainings/PersonalTrainingsTypes?timestamp=0` — PT session-type
catalogue (`name`, `duration`, `productId`). `personalTrainingTypeId` on a PT
booking points here.

### Products & pricing

`GET /v1/Products/Products?timestamp=0` — purchasable products/services:

```json
{
  "name": "Squash 1 hour",
  "description": "",
  "type": "Service",
  "availableFor": "Everyone",
  "defaultPriceGross": { "value": "50.00", "currencyIso": "EUR" },
  "validityPeriodInSeconds": null,
  "isAvailable": true,
  "isVisibleForSale": true,
  "companyId": 251,
  "id": 0
}
```

- `GET /v1/Products/ProductsCategories?timestamp=0` — category tree (`name`,
  `order`, `parentCategoryId`).
- `GET /v1/Products/ProductsProductsCategories?timestamp=0` — join `productId` ↔
  `productCategoryId`.
- `GET /v1/Products/ProductsClubs?timestamp=0` — per-club price overrides
  (`priceGross`, `productId`, `clubId`).
- `GET /v1/Products/AccountProducts?timestamp=0` — products the account owns
  (`quantity.{initialQuantity,currentQuantity}`, `purchaseDateUtc`,
  `expireDateUtc`).
- `GET /v1/Products/DiscountedProductPrice?...` — computed price for a product:
  `{ "productId": 0, "clubId": 962, "gross": 3.0, "net": 2.44, "vat": 0.56 }`.
- `GET /v1/Products/ProductsPaymentsPlans` — empty in capture.

### Engagement & timeline

`GET /v1/Timeline/Timeline?timestamp=0` — the account's activity feed:

```json
{ "accountId": 0, "activityType": "ClubVisit", "trackingServiceId": 16037, "startDate": "2026-04-20T09:31:58+00:00", "id": 0 }
```

`GET /v1/Timeline/TimelineElementsDetails?timestamp=0` — key/value detail rows for
a timeline element (`timelineElementId`, `type`, `value`, `valueType`), e.g.
`type: "ClubName", value: "West Wood Club Dun Laoghaire"`.

`GET /v1/Referrals/ReferralRule?timestamp=0` — referral programme copy (`title`,
`description`). `GET /v1/Referrals/ReferralsPrizes`, `GET /v1/Campaigns/Banners`,
`GET /v1/PushNotifications/Notifications`, `GET /v1/Goals/Goals` — empty in
capture.

### Fitness tracking (third-party)

These drive connections to external wearables/services — the OAuth flows behind
the `refreshToken`/`oauthToken` classes in the app, unrelated to the PerfectGym
session.

`GET /v1/TrackingServices/Services?timestamp=0` — available services and their
OAuth config:

```json
{
  "type": "Fitbit",
  "description": "The most popular fitness wearable",
  "connectionDetails": {
    "authMethod": "OAuth2",
    "authUrl": "https://www.fitbit.com/oauth2/authorize?client_id=...&redirect_uri=pgg://fitbit.callback&scope=activity%20profile%20weight",
    "redirectUrl": "pgg://fitbit.callback"
  },
  "color": "#00B0B8",
  "iconUrl": "https://.../fitbit_icon.png",
  "id": 0
}
```

- `GET /v1/TrackingServices/ServicesActivities?timestamp=0` — activity types per
  service (`activityType`, `trackingServiceId`).
- `GET /v1/TrackingServices/ServicesActivitiesConfigurations?timestamp=0` —
  per-account on/off per activity (`trackingServiceActivityId`, `isTurnedOn`).
- `GET /v1/TrackingServices/ServicesConnections` — the account's active
  connections. Empty in capture.

### Settings, auth & lifecycle

`GET /v1/FeaturesSettings/FeaturesSettings?timestamp=0` — per-tenant feature
flags; worth checking before assuming a feature works:

```json
{ "featureName": "ClubWhoIsIn", "isAvailable": true, "companyId": 251, "id": 0 }
```

Observed flags include `MobileCheckIn`, `Classes`, `ClubWhoIsIn`, `Ratings`,
`PersonalTrainings`, `FacilityBooking`, `Goals`, `PerfectScore`, `Instructors`
(available) and `FamilyBooking`, `ContractPayments`, `ProductPayments`, `Courses`
(unavailable).

`GET /v1/Clubs/Contacts`, `Clubs/Equipment`, `Clubs/Photos`, `Clubs/Urls`,
`Clubs/Favourites` (all `companyId`+`timestamp`) — per-club detail lists, all
empty in capture.

`GET /v1/Authorize/OnlineJoining` — returns `{ "onlineJoiningUrl": null }` (sign-up
web flow, disabled here).

`POST /v1/Authorize/VerifyEmail` — pre-login check; returns `{ "action": "LogIn" }`
(vs a sign-up action) to decide whether an email already has an account.

`POST /v1/ApplicationLifetime/ApplicationStarted` and
`POST /v1/ApplicationLifetime/ApplicationNeedsRefreshedUserData` — telemetry/sync
pings; both return `null` data. Not needed by the integration.
