import btdht
import binascii
dht = btdht.DHT()
dht.start()  # now wait at least 15s for the dht to boostrap
#init socket for 4c323257aa6c4c5c6ccae118db93ccce5bb05d92
#Bootstraping
print(dht.get_peers(binascii.a2b_hex("0403fb4728bd788fbcb67e87d6feb241ef38c75a")))
