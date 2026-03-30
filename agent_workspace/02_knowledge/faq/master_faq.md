# KOMMU MASTER FAQ (FULL REBUILD - SINGLE SOURCE OF TRUTH)

Last updated: 29 Mar 2026 (install positioning: self-install encouraged)

# SECTION 1: INTENTS (CUSTOMER-FACING)

<!-- sop-sync:start -->
## intent: product_overview
aliases:
- what is kommuassist
- what does it do
- what is kommu
- tell me about your product
- what do you sell
- what is adas aftermarket
- what is the added value of Kommu
- difference with original adas
answer:
KommuAssist is an advanced driving assistance system (ADAS) that can control gas, brake and steering. It is mainly used for highway driving and traffic jam assist. It is an aftermarket device that you install in your existing car to get self-driving-like capabilities. It greatly enhances the cruise function and safety by ensuring the steering control stays 100% active with multi-priority decision-making AI model (detecting lane lines, lead car, road borders, divider etc.). Hands on wheel alert is replaced with driver facial attentiveness monitoring to allow for more driving convenience. The braking and acceleration are also made more comfortable with our double camera system that can detect the lead vehicle more confidently for the AI software to impose smoother controls.

## intent: software_stack
aliases:
- what software does it run
- openpilot
- bukapilot
- open source
- what code
answer:
KommuAssist runs bukapilot, a fork of openpilot. You can read the open source software here: https://github.com/kommuai/bukapilot/tree/release

## intent: ka2_modes
aliases:
- driving distance
- distance settings
- ka2 mode
- chill mode
- aggressive mode
- normal mode
- following distance
answer:
KA2 has 3 driving modes:
- Chill (3 bars): relaxed driving, may not reach set speed, larger following distance
- Normal (2 bars): balanced driving style
- Aggressive (1 bar): closer following distance, will not stop at traffic lights or speed bumps

## intent: ka1_vs_ka2
aliases:
- difference between ka1 and ka2
- compare ka1 ka2
- should i buy ka1 or ka2
- ka2 upgrade from ka1
- ka1 vs ka2
- which model should i get
- ka1 or ka2 better
answer:
KA2 is a major upgrade over KA1:
- Processor: RK3588 (KA2) vs Snapdragon 821 (KA1)
- Cameras: 3 automotive-grade cameras (KA2) vs 2 consumer cameras (KA1)
- Cooling: passive cooling (KA2) vs fan cooling (KA1)
- More powerful AI processing and continuous software updates
If you want smoother long-term performance and faster updates, KA2 is recommended.

## intent: pricing
aliases:
- price
- pricing
- how much
- cost
- berapa harga
- what is the price
- how much does it cost
- monthly price
- installment
answer:
For most customers, the Rent to Own (RTO) plan is the easiest start: RM175/month + RM1,999 deposit, with 3-year warranty included. If you prefer outright purchase, I can share the full cash price too.

## intent: full_cash_price
aliases:
- full price
- cash price
- outright price
- one time payment
- buy outright
- pay in full
answer:
If you prefer full cash purchase, KA2 is RM4,999. If you'd like, I can also compare this with the RTO option (RM175/month + RM1,999 deposit) so you can pick what feels most comfortable.

## intent: install_booking
aliases:
- can i install now
- book installation
- installation appointment
- when can i come for install
- how to install
- schedule install
- booking
- walk in install
- i want to install
- just bought can i come
- install myself
- self install
- diy install kommuassist
answer:
Kommu **encourages self-installation**: many customers fit KommuAssist themselves using the installation guide, product videos, and the **KommuAI** app. If you are comfortable with basic in-car wiring and following safety steps (engine off when plugging electronics, correct USB ports on the relay, etc.), you can install at home or wherever is convenient. **Optional HQ help:** if you prefer on-site support at Kommu, you can book an installation slot — customers often receive an **appointment link by email after checkout** for that option. When done at HQ, expect about **30 minutes** total (roughly **15 minutes** hardware + **15 minutes** briefing on using the device). If you get stuck during self-install, contact **support@kommu.ai** with photos or error details.

## intent: office_info
aliases:
- where is kommu office
- office location
- can i walk in
- hq address
- where are you located
- address
- how to get there
- directions
- office hours
- opening hours
answer:
Kommu HQ: EmHub, Block B-03-31, Kota Damansara, 47810 Petaling Jaya, Selangor.
Waze: https://waze.com/ul/hw281zr717
Google Maps: https://maps.app.goo.gl/wbUA1fUzTxRxUiVK6
For entrance access: we will provide 1 day prior your test drive/installation slot
Video guide: https://youtu.be/63PJBqvxvsY
Hours: Mon-Fri 10AM-6PM, Sat by appointment only.

## intent: installation_time
aliases:
- how long install
- installation duration
- install takes how many minutes
- how long does installation take
answer:
Plan about **30 minutes** end to end for hardware installation plus a first-time walkthrough of how to use KommuAssist — whether you **self-install** or have **optional** help at Kommu HQ. Times vary slightly with experience and vehicle access.

## intent: kommuassist_installation_guide
aliases:
- how to install kommuassist
- kommuassist installation steps
- installation procedure
- hardware installation kommuassist
- relay setup kommu
- kommu relay installation
- kommu vision mount
- windshield mount kommuassist
- cable routing installation
- obd kommu power
- installation sop
- car fingerprint kommuassist
- vehicle fingerprint bukapilot
- controls waiting to start
- usb cable swapped relay
answer:
Standard KommuAssist installation (per Kommu Installation & Briefing SOP) uses the **Kommu Relay**, **Kommu Vision** camera, **Kommu Power** at the OBD port, and USB-C cabling. Kommu **encourages capable customers to self-install** using this procedure; the steps below are the same reference workflow used for training and optional on-site support. **Do not treat HQ installation as required** — it is an extra option if you want hands-on help. Work carefully around **airbags** and **high-voltage** areas; if anything is unclear, pause and ask **support@kommu.ai** before forcing connectors.

**Video:** KommuAssist Installation Guide (internal training video title in SOP).

**What’s in the box (conceptually):** Relay with brand-specific harness, long and short USB-C cables, Kommu Power (OBD), Kommu Vision on its mount, electrostatic windshield sticker, and related hardware as shipped for your vehicle.

**A. Kommu Relay**
- Remove the car’s ADAS cover with a plastic pry tool.
- **Engine off** — unplug the **original ADAS connector**.
- Plug in the **Kommu Relay** using the **brand-specific harness**.
- **Engine on** — confirm **no ADAS/error warnings** on the instrument cluster.
- Plug the **long USB-C** into the Relay port labeled **Vision**, and the **short USB-C** into the port labeled **Power** (do not swap these; swapped cables can cause “camera on but no control”).
- Seat the relay assembly and refit the ADAS cover.

**B. Cable management**
- Partially remove the **door weather strip** on the routing side.
- Loosen the **right A-pillar airbag plastic trim** (route safely around/below airbag as trained).
- Run the **long USB-C** behind the airbag area if applicable, then along the weather-strip gap to the bottom of the steering-dash panel (side hole).
- Route above the **steering rack** so the cable cannot tangle with the driver’s feet.
- Connect the lower end to **Kommu Power**, then plug Kommu Power into the **OBD** port.
- Slip the upper section into the **headliner**; tuck excess into the weather strip / A-pillar area.
- Refit A-pillar trim, then the weather strip.

**C. Kommu Vision**
- Clean the windshield with an **alcohol swab**.
- Apply the **electrostatic sticker** with face **“1”** to the glass **just below the ADAS cover**; no trapped air bubbles.
- Stick the **mount (with Vision)** to face **“2”** of the sticker — **vertical and centered**.
- Remove Vision momentarily, press the mount firmly so the **3M** fully contacts the sticker (check from outside the car).
- **Engine off** — connect the **short cable’s L-shaped end** to the Vision port (always **engine off** when plugging electronics).
- Remount Vision, then continue to terms briefing and user tutorial.

**Briefing highlights for the customer**
- Data collection improves software and support; drive logs and usage appear in the **mobile app**.
- KommuAssist **enhances** factory **ACC + LKA**; it is **not** full autonomy — **Level 2**: the **driver stays responsible**.
- **1 year** hardware warranty with ongoing software/firmware support; warranty may be void for **unauthorized** hardware tampering or unofficial software changes — **self-install following Kommu’s guide is fine**.
- On-screen cues: **white** lane lines, **red** divider/border/grass, **thick path** = planned path; **yellow triangle** = lead vehicle (explains braking behavior).
- Engagement/disengagement matches the **stock ACC** method (including brake or **CANCEL** to disengage). **Driver monitoring** replaces steering touch — distraction triggers visual/audio alerts.
- Stock ADAS (AEB, PCW, LDP, etc.) remains; Kommu adds sensing to strengthen ACC/LKA. **Bukapilot** does **not** reliably detect traffic lights, potholes, or speed bumps.
- **Device** page: **Dongle ID** for app pairing; **Reset calibration** if lane detection feels wrong. **Personalised**: follow distance, path skew, fan speed, auto power-off. **Network**: Wi‑Fi for log upload and updates. **Software**: check version, use **Check** until last update shows **now**, then **reboot** to apply downloads.

**Common issues (quick fixes)**
- **Cluster errors:** Reseat ADAS/Relay connector with **Vision unplugged** until cleared. On some **Perodua** cars the lamp may linger until Vision fully boots.
- **Stuck on “getting ready” / no camera view:** Often **GPS not synced** yet — wait; it should come online.
- **Device error / no camera view:** Possible **bad flash** — **reboot**; firmware often self-recovers.
- **Camera malfunction:** Faulty Vision unit — warranty/service path.
- **Calibration invalid:** Camera needs ~**50% road / 50% sky** — remount; if the **case is deformed**, return for case service.
- **“Car unrecognized” / dashcam mode:** Set **Software → Fingerprint** to the exact string for the vehicle (see table). If the car is **not listed**, contact **support@kommu.ai**.
- **“Controls waiting to start”:** **Typo in fingerprint** — re-check against the table.
- **Camera on but no control:** **USB-C to Relay swapped** — Vision vs Power ports.

**Car fingerprint names (Table 1)**
- Perodua Alza → `Perodua Alza`
- Perodua Ativa → `Perodua Ativa`
- Perodua Myvi → `Perodua Myvi PSD`
- Proton S70 → `Proton S70`
- Proton X50 → `Proton X50`
- Proton X90 → `Proton X90`
- BYD Atto 3 → `BYD Atto 3`
- Toyota Alphard / Vellfire → `Toyota Alphard 2020`
- Toyota Corolla → `Toyota Corolla TSS2 2019`
- Toyota Corolla Cross → `Toyota Corolla Hybrid TSS2 2019`

**KA2 note:** Newer KA2 units use the **KommuAI** app for many settings, calibration, and diagnostics; always follow the **printed port labels** on the device (never apply **12V vehicle power** to the **diagnostic/data** USB). When in doubt, use app guidance and support.

## intent: warranty
aliases:
- warranty period
- how long warranty
- warranty coverage
- what does warranty cover
- warranty claim
- is it under warranty
- device warranty
answer:
Warranty is 1 year for cash purchases, 3 years for RTO (Rent to Own). It covers manufacturing defects but excludes physical damage or misuse. If you want to check a specific device's warranty status, share your dongle ID and we can look it up.

## intent: shipping
aliases:
- when will it ship
- delivery schedule
- shipping date
- courier timing
- when do you ship
- delivery time
answer:
We ship on Wednesdays and Fridays when stock is available. If batch assembly affects timing, we'll provide the latest ETA.

## intent: sim_usage
aliases:
- sim card
- need sim
- data plan
- mobile data
- does it need internet
answer:
A SIM card is optional but recommended. Internet connectivity enables: driving log uploads, over-the-air software updates, and remote support from our team.

## intent: hotspot
aliases:
- can use wifi
- hotspot connection
- phone hotspot
- wifi connection
- connect to phone
answer:
Yes, KommuAssist can connect to your phone's WiFi hotspot through the companion app for internet connectivity.

## intent: max_speed
aliases:
- maximum speed
- speed limit
- how fast can it go
- top speed
- speed cap
answer:
KommuAssist follows the car's factory ACC speed limit. For Perodua vehicles, the maximum is typically 140 km/h.

## intent: legality
aliases:
- is it legal
- legal in malaysia
- allowed on road
- regulation
- road legal
answer:
ADAS aftermarket devices are not specifically regulated in Malaysia. KommuAssist operates in a grey area but is aligned with the national autonomous vehicle (AV) committee's direction.

## intent: test_drive
aliases:
- can i try
- test drive
- demo
- try before buy
- test it first
- book test drive
- schedule test drive
- calendly test drive
answer:
Yes, test drives are available. You can try it on our Kommu vehicle or bring your own supported car to our office. Book your slot here: https://calendly.com/kommuassist/test-drive.

## intent: return_policy
aliases:
- refund policy
- can i refund
- return and refund
- cancellation refund
- money back
- can i return it
answer:
No refunds are available after shipment or installation. Please reach out if you have specific concerns — we're happy to help troubleshoot or clarify before you buy.

## intent: transfer_device
aliases:
- can i transfer
- move to another car
- transfer device
- switch cars
- use on different car
answer:
You can transfer the device to another car if that car is also supported and uses the same connector type.

## intent: unsupported_vehicle
aliases:
- car not supported
- unsupported car
- no support for my car
- compatibility failed
- my car cannot use
answer:
A car needs factory ACC (Adaptive Cruise Control) and LKA (Lane Keep Assist) to be supported. It must also use CAN bus (not FlexRay). If the car is supportable but not yet on our list, we may be able to add support — the vehicle typically needs to stay at our HQ for at least 3-5 days for connector work, data collection, and reverse engineering.

## intent: beta_program
aliases:
- borrow my car
- support my vehicle model
- can i lend my car
- vehicle development program
- car lending program
- support new car
- beta support new car
answer:
If your car is supportable but not yet supported, you can work with us on beta support. The car usually needs to be at Kommu HQ for at least 3-5 days so we can find the right connector, run data collection, and do reverse engineering work. In return you may receive an RM300 discount (confirm current terms with sales). A live agent will coordinate schedule and technical checks.

## intent: rto_details
aliases:
- rent to own details
- rto plan
- monthly payment plan
- deposit and monthly
- installment plan
- hire purchase
answer:
Our RTO plan is RM175/month with an RM1,999 deposit. Device ownership transfers to you after all payments are completed, and RTO includes a 3-year warranty. Read the terms here: https://kommu.ai/rto-terms/. If helpful, I can also share the full cash option for comparison.

## intent: reset_procedure
aliases:
- how to reset device
- reboot ka2
- restart kommuassist
- hard reset steps
- device restart
- power cycle
answer:
To reset: power off the device, wait 20-30 seconds, then power it back on. Make sure you have stable power input and internet (hotspot) connected afterward. If the issue persists after reset, share your error code or symptom and we'll investigate.

## intent: batch_delivery_tracking
aliases:
- batch status
- what batch am i in
- delivery batch tracking
- eta for my batch
- when is my device coming
- order eta
answer:
Batch timelines depend on stock availability, assembly progress, and installation slot scheduling. Share your order details and we can check the latest ETA.


# SECTION 2: WORKFLOWS (INTERNAL)

## intent: no_logs
aliases:
- no driving logs
- logs not uploading
- missing logs
- log upload failed
answer:
Check your internet connection first. Logs require an active data connection (SIM or hotspot). If the connection is fine, the server may be temporarily down — try again later.

## intent: overheating
aliases:
- device is hot
- overheating warning
- temperature too high
- device overheats
answer:
Internal temperatures up to 70°C are normal during operation. If you see a persistent overheat warning, ensure the device is not in direct sunlight and check that ventilation around it is not blocked.

## intent: led_status
aliases:
- led color meaning
- what do the lights mean
- led indicator
- light colors
- status light
answer:
LED status colors:
- Purple: device starting up
- Yellow: idle / standby
- Blue: ready to engage
- Green: actively engaged (driving assist on)
- Orange: warning condition
- Red: error — check device

## intent: device_not_on
aliases:
- device cannot turn on
- no power on ka2
- black screen device
- ka2 not booting
- device won't start
- no led at all
answer:
Check that the power connector is securely seated and that the car ignition is on. Look for any LED activity. If there is absolutely no LED response after confirmed power input, it may indicate a board-level power issue — we'll need to arrange service. Share your dongle ID so we can check your warranty.

## intent: gps_issue
aliases:
- gps not working
- no gps signal
- gps problem
- location not found
- gps fix
answer:
GPS needs clear sky view to get a fix. Try driving to an open area. If you're using the device indoors or in a covered parking structure, GPS won't lock on. A phone hotspot connection can help with assisted GPS.

## intent: kommuai_app_overview
aliases:
- kommuai app
- mobile app settings
- ka2 app
- phone app for ka2
- app reboot format sd
- recalibration app
answer:
For KA2, most settings, calibration, and diagnostics go through the **KommuAI** mobile app. From the app you can reboot the device, format the SD card, run recalibration, enable quiet mode, toggle assisted lane change, toggle lane departure warning (LDW), adjust ADAS-related options, open the **Visualization** tab (paths, lanes, distances, driver monitoring), and manage logs / feedback. If a user needs step-by-step guidance for settings or calibration, always point them to the KommuAI app first.

## intent: kommuai_app_visualization
aliases:
- visualization tab
- error info on app
- lane lines app
- driver monitoring app
answer:
In the KommuAI app, the **Visualization** tab shows live driving visualization: paths, lane lines, distance settings, and driver monitoring state. It also surfaces **error information** that is very useful when debugging — ask the user to note or screenshot what appears there when reporting a problem to technical support.

## intent: kommuai_app_logs
aliases:
- submit full logs
- app logs feedback
- driving logs app
answer:
The **Logs** section in the KommuAI app shows driving logs. Users can submit feedback from there and use **Submit full logs** when reporting an issue. Remind them to write a **clear, descriptive** summary of the problem (when it happens, what they were doing, error text if any) so support can act faster.

## intent: kommuai_app_settings
aliases:
- bluetooth settings ka2
- experimental mode
- sim 2g 4g app
- upload status logs
- wifi fingerprint app
- ios app slow settings
answer:
The **Settings** page in the KommuAI app connects to KA2 over **Bluetooth**. If another phone or device is also using Bluetooth heavily, it can **contest the connection** and cause unstable or missing settings — disconnect extra Bluetooth devices when possible. On **iOS**, if the settings page does not show or is very slow, **force-quit (kill) the app** and reopen; connection often recovers. Settings may include **Experimental mode** (alpha / testing features), **Wi‑Fi** setup, and **fingerprint** selection. For the built-in SIM: **2G** in the app usually means **no usable data connection**; **4G** means there is connection. If logs seem empty, check whether data has already uploaded — the settings area shows **remaining upload** status. If problems persist after checking connectivity and uploads, escalate to technical support.

## intent: kommuai_app_bluetooth_issue
aliases:
- bluetooth unstable ka2
- cannot connect app bluetooth
answer:
Unstable Bluetooth to KA2 is often caused by **other devices** competing for the same radio. Ask the user to turn off Bluetooth on other phones/wearables temporarily, move closer to the device, and retry. On **iOS**, killing and reopening the KommuAI app often fixes a stuck settings connection.

## intent: ka2_usb_ports_warning
aliases:
- which usb port ka2
- diagnostic port power port
- wrong usb burned
- silicone cover usb
answer:
**Important — warranty-critical:** KA2 has **two USB ports**. The **power port** is at the **edge** of the device and is the one meant for **in-car power**. The **diagnostic / data port** is separate and is usually covered with a **silicone plug**. **Never apply 12V vehicle power to the diagnostic port** — it can destroy the board. **Damage from wrong-port power is not covered under warranty.** If unsure, ask the user to send a photo of the ports before advising.

## intent: flash_kommu_restore
aliases:
- flash.kommu.ai
- factory reset ka2 software
- reflash ka2
- recovery button ka2
- bootloader ka2
answer:
To restore KA2 to **factory software**, use **https://flash.kommu.ai** and follow the on-screen steps. Typically you connect **5V non–Power Delivery** power **and** the **diagnostic** USB to a **PC or laptop**, then flash using **Chrome**. **Only Linux and macOS have been tested** as working environments for this flow. **Do not unplug** the device while flashing is in progress. If the device is badly bricked, you may need to remove the **top four screws**, press the **recovery** button **while** applying power to enter loader mode — but usually you can use the KommuAI app **Settings → Enter boot loader** instead.

## intent: ativa_myvi_braking_sound
aliases:
- braking sound
- abs brake pump
- car brake making noise every 3 seconds
answer:
The stock ACC on the Perodua Ativa and Perodua Myvi is not capable of braking the vehicle all the way to a standstill (0 km/h). Kommu addressed this limitation by transmitting repeated brake commands approximately every 3 seconds. This approach was necessary because the ABS brake pump would still release brake pressure even when commands were sent at a higher frequency. As a result, there is a slight nudge each time the pump releases and re-clamps the brake disc.

# SECTION 5: DYNAMIC

## workflow: repair_flow
steps:
1. check warranty status
2. if under warranty -> arrange service
3. if not under warranty -> quote repair price
4. collect payment
5. arrange repair/install appointment

## data: ka1_parts_prices_ringgits
controller_board: 300
motherboard: 400
kommu_power: 50
vehicle_connector: 150
relay: 50
fan: 30
mount: 30
screen: 150
front_case: 200
back_case: 200
shipping_local: 8

## data: bank
name: Kommu Sdn Bhd
bank: Maybank
account: 514208667737

## data: shipment_address
name: Wong Kean Wei
phone: 0149676780
address: Block B-03-31, Emhub, Kota Damansara, 47810 Petaling Jaya, Selangor
# SECTION 4: TROUBLESHOOTING

## dynamic: batch_status
batch: 4
status: assembling
eta: April 2026
valid_from: 2026-03-01
valid_until: 2026-12-31
priority: 10
<!-- sop-sync:end -->


## intent: ka2_error_1003_logs_missing
aliases:
- KA2 error 1003 logs missing
- error 1003
answer:
Resolved by reboot and firmware update. Power cycle the device and ensure it's connected to internet to pull the latest firmware.

<!-- provenance: conv=111 msg=2 agent=9 product=KA2 -->
<!-- provenance: kommuassist_installation_guide sourced from support@kommu.ai Drive "AI-Agent Public Knowledge/Standard Operating Procedures/Installation & Briefing SOP.docx" (last edited 7 Jul 2024 in doc) -->
