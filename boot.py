import usb_cdc
import supervisor
import microcontroller

usb_cdc.enable(console=True, data=True)

print("USB data port enabled")
if microcontroller.nvm:
    print("NVM: ", len(microcontroller.nvm))
if microcontroller.watchdog:
    print("Watchdog: {}".format(microcontroller.watchdog))
if microcontroller.cpus:
    for i,c in enumerate(microcontroller.cpus):
        print("Reset Reason[cpu{}]: {}".format(i, c.reset_reason))
else:
    print("Reset Reason: {}".format(microcontroller.cpu.reset_reason))
print("Run Reason: {}".format(supervisor.runtime.run_reason))
