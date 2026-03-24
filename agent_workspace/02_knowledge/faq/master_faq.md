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
answer:
Yes, test drives are available. You can try it on our Kommu vehicle or bring your own supported car to our office.

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
A car needs factory ACC (Adaptive Cruise Control) and LKA (Lane Keep Assist) to be supported. It must also use CAN bus (not FlexRay). If the car is supportable but not yet on our list, we may be able to add support — we'd just need to borrow the car for a few hours.

## intent: beta_program
aliases:
- borrow my car
- support my vehicle model
- can i lend my car
- vehicle development program
- car lending program
- support new car
answer:
If your car is supportable but not yet supported, you can lend it to us for development. In return, you get an RM300 discount. Our live agent will coordinate the schedule and technical checks.

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

# SECTION 5: DYNAMIC

## dynamic: batch_status
batch: 4
status: assembling
eta: April 2026
<!-- sop-sync:end -->


## intent: ka2_error_1003_logs_missing
aliases:
- KA2 error 1003 logs missing
- error 1003
answer:
Resolved by reboot and firmware update. Power cycle the device and ensure it's connected to internet to pull the latest firmware.

<!-- provenance: conv=111 msg=2 agent=9 product=KA2 -->
