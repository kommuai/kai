# KOMMU MASTER FAQ (FULL REBUILD - SINGLE SOURCE OF TRUTH)

Last updated: 24 Mar 2026

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
answer:
KommuAssist is an advanced driving assistance system (ADAS) that can control gas, brake and steering. It is mainly used for highway driving and traffic jam assist. It is an aftermarket device that you install in your existing car to get self-driving-like capabilities on supported roads.

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
answer:
KommuAssist KA2 is RM4,999 (cash) or RM175/month + RM1,999 deposit under our Rent to Own (RTO) plan.

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
answer:
Installation is by appointment after checkout. You will receive an appointment link in your email once payment has been made. The on-site process takes about 30 minutes (15 min installation + 15 min briefing on how to use the device).

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
For entrance access: https://emhub.smartserva.com/visitor_pass.php?v=0212G1XZ78P0I5T8AUHJAWWYYEFASM
Video guide: https://youtu.be/63PJBqvxvsY
Hours: Mon-Fri 10AM-6PM, Sat by appointment only.

## intent: installation_time
aliases:
- how long install
- installation duration
- install takes how many minutes
- how long does installation take
answer:
About 30 minutes total — 15 minutes for hardware installation and 15 minutes for briefing on how to use KommuAssist.

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
Yes, test drives are available. You can try it on our Kommu vehicle or bring your own supported car to our office. **Book or reschedule here:** https://calendly.com/kommuassist/test-drive — whenever someone asks about a test drive, demo, or trying before buying, share this link so they can pick a slot.

## intent: return_policy
aliases:
- refund policy
- can i refund
- return and refund
- cancellation refund
- money back
- can i return it
answer:
No refunds are available after purchase. Please reach out if you have specific concerns — we're happy to help troubleshoot or clarify before you buy.

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
A car needs factory ACC (Adaptive Cruise Control) and LKA (Lane Keep Assist) to be supported. It must also use CAN bus (not FlexRay). If the car is supportable but not yet on our list, we may be able to add support — the vehicle typically needs to stay at our HQ for at least a full day for connector work, data collection, and reverse engineering.

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
If your car is supportable but not yet supported, you can work with us on beta support. The car usually needs to be at Kommu HQ for at least one full day so we can find the right connector, run data collection, and do reverse engineering work. In return you may receive an RM300 discount (confirm current terms with sales). A live agent will coordinate schedule and technical checks.

## intent: rto_details
aliases:
- rent to own details
- rto plan
- monthly payment plan
- deposit and monthly
- installment plan
- hire purchase
answer:
Our RTO plan is RM175/month with an RM1,999 deposit. Device ownership transfers to you after all payments are completed. RTO includes a 3-year warranty. Contact us for the latest exact terms.

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

## workflow: repair_flow
steps:
1. check warranty status
2. if under warranty -> arrange service
3. if not under warranty -> quote repair price
4. collect payment
5. arrange repair/install appointment


# SECTION 3: DATA (REFERENCE)

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
address: Emhub, Kota Damansara

# SECTION 4: TROUBLESHOOTING

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

# SECTION 5: DYNAMIC

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
