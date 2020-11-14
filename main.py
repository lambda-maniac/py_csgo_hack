""" =====================
::: Made by: LordZarkares
===================== """

from math import asin, atan2
import pymem.process
import keyboard
import pymem

class Vector3:
    def __init__(self, x = 0.0, y = 0.0, z = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __add__(self, other):
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    def __sub__(self, other):
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
    def __mul__(self, scale):
        return Vector3(self.x * scale, self.y * scale, self.z * scale)
    def __str__(self):
        return f"(x: {str(self.x)}, y: {str(self.y)}, z: {str(self.z)})"
    def __repr__(self):
        return f"(x: {str(self.x)}, y: {str(self.y)}, z: {str(self.z)})"

    def distanceTo(self, other):
        delta = other - self; return ((delta.x ** 2) + (delta.y ** 2) + (delta.z ** 2))**(0.5)

pm = pymem.Pymem()
pm.open_process_from_name("csgo.exe")

client = pymem.process.module_from_name(
            pm.process_handle,
            "client.dll"
).lpBaseOfDll
engine = pymem.process.module_from_name(
            pm.process_handle,
            "engine.dll"
).lpBaseOfDll

""" =============================================
::: Offsets needed, as they always change, sorry.
============================================= """
offset = {
    "dwClientState_GetLocalPlayer" : (0x0),
    "dwEntityList"                 : (0x0),
    "dwLocalPlayer"                : (0x0),
    "dwClientState"                : (0x0),
    "dwClientState_ViewAngles"     : (0x0),
    "dwGlowObjectManager"          : (0x0),
    "m_bDormant"                   : (0x0),

    "netvar"               : {
        "m_iTeamNum"       : (0x0),
        "m_vecOrigin"      : (0x0),
        "m_dwBoneMatrix"   : (0x0),
        "m_vecViewOffset"  : (0x0),
        "m_iHealth"        : (0x0),
        "m_bSpottedByMask" : (0x0),
        "m_iGlowIndex"     : (0x0),
    }
}

def getPlayer(index: int) -> int: 
    return pm.read_int(client + offset["dwEntityList"] + (index * 0x10))

def getLocalPlayer() -> int:
    return pm.read_int(client + offset['dwLocalPlayer'])
    
def getPlayerTeam(player: int) -> int:
    return pm.read_int(player + offset['netvar']['m_iTeamNum'])

def getPlayerHealth(player: int) -> int:
    return pm.read_int(player + offset['netvar']['m_iHealth'])
    
def isDormant(player: int) -> bool:
    return bool(pm.read_int(player + offset['m_bDormant']))

def getGlowObjectManager() -> int:
    return pm.read_int(client + offset["dwGlowObjectManager"])

def getPlayerGlowIndex(player: int) -> int:
    return pm.read_int(player + offset['netvar']["m_iGlowIndex"])

def sameTeam(player: int) -> bool:
    return getPlayerTeam(player) == getPlayerTeam(getLocalPlayer())

def isDead(player: int) -> bool:
    return getPlayerHealth(player) < 1 or getPlayerHealth(player) > 100

def isVisible(player: int) -> bool:
    clientState = pm.read_int(engine + offset['dwClientState'])
    localPlayerId = pm.read_int(clientState + offset['dwClientState_GetLocalPlayer'])

    spottedByMask = pm.read_int(player + offset['netvar']['m_bSpottedByMask'])

    return spottedByMask & (1 << localPlayerId)

def getPlayerLocation(player: int) -> Vector3:
    return Vector3(
        x = pm.read_float(player + offset['netvar']['m_vecOrigin'] + 0x0),
        y = pm.read_float(player + offset['netvar']['m_vecOrigin'] + 0x4),
        z = pm.read_float(player + offset['netvar']['m_vecOrigin'] + 0x8),
    )

def getPlayerBoneLocation(player: int, bone: int) -> Vector3:
    boneMatrix = pm.read_int(player + offset['netvar']['m_dwBoneMatrix'])
    return Vector3(
        x = pm.read_float(boneMatrix + 0x30 * bone + 0x0C),
        y = pm.read_float(boneMatrix + 0x30 * bone + 0x1C),
        z = pm.read_float(boneMatrix + 0x30 * bone + 0x2C),
    )

def getLocalPlayerViewOffset() -> Vector3:
    return Vector3(
        x = pm.read_float(getLocalPlayer() + offset['netvar']['m_vecViewOffset'] + 0x0),
        y = pm.read_float(getLocalPlayer() + offset['netvar']['m_vecViewOffset'] + 0x4),
        z = pm.read_float(getLocalPlayer() + offset['netvar']['m_vecViewOffset'] + 0x8),
    )

def getLocalPlayerViewAngles() -> Vector3:
    clientState = pm.read_int(engine  + offset['dwClientState']); return Vector3(
        x = pm.read_float(clientState + offset['dwClientState_ViewAngles'] + 0x0),
        y = pm.read_float(clientState + offset['dwClientState_ViewAngles'] + 0x4),
        z = pm.read_float(clientState + offset['dwClientState_ViewAngles'] + 0x8),
    )

def writeLocalPlayerViewAngles(x: float, y: float) -> None:
    if y >  180.0: y -= 360.0
    if y < -180.0: y += 360.0
    if x >   89.0: x -= 180.0
    if x <  -89.0: x += 180.0

    clientState = pm.read_int(engine + offset['dwClientState'])
    pm.write_float(clientState + offset['dwClientState_ViewAngles'] + 0x0, x)
    pm.write_float(clientState + offset['dwClientState_ViewAngles'] + 0x4, y)

def forceLocalPlayerAimTo(target: Vector3) -> None:
    localPlayerHead = getPlayerLocation(getLocalPlayer()) + getLocalPlayerViewOffset()

    delta       = target - localPlayerHead
    deltaLength = localPlayerHead.distanceTo(target)

    writeLocalPlayerViewAngles(-asin(delta.z / deltaLength) * (180.0 / 3.14159235368979), 
                               atan2(delta.y , delta.x    ) * (180.0 / 3.14159235368979))

def glowPlayer(player: int) -> None:
    entityGlow  = getPlayerGlowIndex(player)
    glowManager = getGlowObjectManager()

    if getPlayerTeam(player) == getPlayerTeam(getLocalPlayer()):
        pm.write_float(glowManager + entityGlow * 0x38 + 0x4 , float(0))
        pm.write_float(glowManager + entityGlow * 0x38 + 0x8 , float(0))
        pm.write_float(glowManager + entityGlow * 0x38 + 0xC , float(1))
        pm.write_float(glowManager + entityGlow * 0x38 + 0x10, float(1))
        pm.write_int  (glowManager + entityGlow * 0x38 + 0x24, int  (1))
    else:
        pm.write_float(glowManager + entityGlow * 0x38 + 0x4 , float(1))
        pm.write_float(glowManager + entityGlow * 0x38 + 0x8 , float(0))
        pm.write_float(glowManager + entityGlow * 0x38 + 0xC , float(0))
        pm.write_float(glowManager + entityGlow * 0x38 + 0x10, float(1))
        pm.write_int  (glowManager + entityGlow * 0x38 + 0x24, int  (1))

def findClosestValidEnemy() -> bool or int:

    closestDistance      = 99999999.99
    closestDistanceIndex = -1

    for i in range(1, 32):
        entity = getPlayer(i)

        if not entity            : continue
        if not isVisible(entity) : continue

        if isDormant(entity)     : continue
        if isDead   (entity)     : continue
        if sameTeam (entity)     : continue

        currentDistance = getPlayerLocation(getLocalPlayer() ).distanceTo( getPlayerLocation(entity))
        
        if  currentDistance      < closestDistance:
            closestDistance      = currentDistance
            closestDistanceIndex = i

    return False if closestDistanceIndex == -1 else closestDistanceIndex

def main():
    while True:
        if keyboard.is_pressed('end'): exit(0)

        if keyboard.is_pressed('shift'):
            entity = findClosestValidEnemy()

            if   entity:forceLocalPlayerAimTo(getPlayerBoneLocation(getPlayer(entity), bone = 8))

        for i in range(1, 32):
            entity = getPlayer(i)

            if   entity:glowPlayer(entity)
            
if __name__ == '__main__' : main()
