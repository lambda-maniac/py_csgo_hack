from math            import asin, atan2, pi

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
        return self.__str__()

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

offset = {
    "dwClientState_GetLocalPlayer" : (0x180),
    "dwEntityList"                 : (0x4DA215C),
    "dwLocalPlayer"                : (0xD892CC),
    "dwClientState"                : (0x588FEC),
    "dwClientState_ViewAngles"     : (0x4D90),
    "dwForceAttack"                : (0x31D2690),
    "dwGlowObjectManager"          : (0x52EA5D0),
    "m_bDormant"                   : (0xED),

    "netvar"               : {
        "m_fFlags"         : (0x104),
        "m_iCrosshairId"   : (0xB3E8),
        "m_iTeamNum"       : (0xF4),
        "m_iShotsFired"    : (0xA390),
        "m_aimPunchAngle"  : (0x302C),
        "m_vecOrigin"      : (0x138),
        "m_dwBoneMatrix"   : (0x26A8),
        "m_vecViewOffset"  : (0x108),
        "m_iHealth"        : (0x100),
        "m_bSpottedByMask" : (0x980),
        "m_iGlowIndex"     : (0xA438),
    }
}

def getPlayer(index: int) -> int: 
    return pm.read_uint(client + offset["dwEntityList"] + (index * 0x10))

def getLocalPlayer() -> int:
    return pm.read_uint(client + offset['dwLocalPlayer'])

def getClientState() -> int:
    return pm.read_int(engine + offset['dwClientState'])
    
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

def sameTeam(playerA: int, playerB: int) -> bool:
    return getPlayerTeam(playerA) == getPlayerTeam(playerB)

def isDead(player: int) -> bool:
    return getPlayerHealth(player) < 1 or getPlayerHealth(player) > 100

def shotsFired(quantity: int):
    return pm.read_uint(getLocalPlayer() + offset["netvar"]["m_iShotsFired"]) > quantity

def isVisible(player: int) -> bool:
    clientState   = getClientState()
    localPlayerId = pm.read_int(clientState + offset['dwClientState_GetLocalPlayer'])

    spottedByMask = pm.read_int(player + offset['netvar']['m_bSpottedByMask'])

    return spottedByMask & (1 << localPlayerId)

def normalizeAngles(x: float, y: float) -> tuple[float, float]:
    if y >  180.0: y -= 360.0
    if y < -180.0: y += 360.0
    if x >   89.0: x -= 180.0
    if x <  -89.0: x += 180.0

    return (x, y)

def getPlayerLocation(player: int) -> Vector3:
    return Vector3(
        x = pm.read_float(player + offset['netvar']['m_vecOrigin'] + 0x0),
        y = pm.read_float(player + offset['netvar']['m_vecOrigin'] + 0x4),
        z = pm.read_float(player + offset['netvar']['m_vecOrigin'] + 0x8),
    )

def getPlayerBoneLocation(player: int, bone: int) -> Vector3:
    boneMatrix = pm.read_uint(player + offset['netvar']['m_dwBoneMatrix'])
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
    clientState = getClientState(); return Vector3(
        x = pm.read_float(clientState + offset['dwClientState_ViewAngles'] + 0x0),
        y = pm.read_float(clientState + offset['dwClientState_ViewAngles'] + 0x4),
        z = pm.read_float(clientState + offset['dwClientState_ViewAngles'] + 0x8),
    )

def writeLocalPlayerViewAngles(x: float, y: float) -> None:
    x, y = normalizeAngles(x, y)

    clientState = getClientState()
    pm.write_float(clientState + offset['dwClientState_ViewAngles'] + 0x0, x)
    pm.write_float(clientState + offset['dwClientState_ViewAngles'] + 0x4, y)

def normalizeRecoil(oldPunch: Vector3) -> tuple[Vector3, Vector3]:
    localPlayer = getLocalPlayer()
    
    punchAngles = Vector3 (
        x = pm.read_float(localPlayer + offset["netvar"]["m_aimPunchAngle"] + 0x0),
        y = pm.read_float(localPlayer + offset["netvar"]["m_aimPunchAngle"] + 0x4),
        z = pm.read_float(localPlayer + offset["netvar"]["m_aimPunchAngle"] + 0x8),
    ) * 2

    viewAnlges  = getLocalPlayerViewAngles()

    newAngle = viewAnlges + oldPunch - punchAngles

    writeLocalPlayerViewAngles(newAngle.x, newAngle.y)

    return punchAngles

def forceLocalPlayerAimTo(target: Vector3) -> None:
    localPlayerHead = getPlayerLocation(getLocalPlayer()) + getLocalPlayerViewOffset()

    delta       = target - localPlayerHead
    deltaLength = localPlayerHead.distanceTo(target)

    writeLocalPlayerViewAngles(-asin(delta.z / deltaLength) * (180.0 / pi), 
                               atan2(delta.y , delta.x    ) * (180.0 / pi))

def glowPlayer(player: int) -> None:
    entityGlow  = getPlayerGlowIndex(player)
    glowManager = getGlowObjectManager()

    if sameTeam(player, getLocalPlayer()):
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

        if isDormant(entity)                   : continue
        if isDead   (entity)                   : continue
        if sameTeam (entity, getLocalPlayer()) : continue

        currentDistance = getPlayerLocation(getLocalPlayer() ).distanceTo( getPlayerLocation(entity))
        
        if  currentDistance      < closestDistance:
            closestDistance      = currentDistance
            closestDistanceIndex = i

    return False if closestDistanceIndex == -1 else closestDistanceIndex

def aimbot():
    entity = findClosestValidEnemy()

    if entity:forceLocalPlayerAimTo(getPlayerBoneLocation(getPlayer(entity), bone = 8))

def triggerbot():
    entityId = pm.read_int(getLocalPlayer() + offset["netvar"]["m_iCrosshairId"])
    entity   = getPlayer(entityId - 1)

    if entityId > 0 and entityId <= 64 and not sameTeam(getLocalPlayer(), entity):
        pm.write_int(client + offset["dwForceAttack"], 6)

def wall():
    for i in range(1, 32):
        entity = getPlayer(i)

        if entity:glowPlayer(entity)

def main():

    evilMode = False
    oldPunch = Vector3(0, 0, 0)

    while True:
        if   keyboard.is_pressed('end')              : exit(0)
        elif keyboard.is_pressed('f1')               : evilMode = not evilMode
        elif keyboard.is_pressed('shift') or evilMode: aimbot()

        triggerbot()
            
        if (shotsFired(1)): oldPunch = normalizeRecoil(oldPunch)
        else              : oldPunch = Vector3(0, 0, 0)

        wall()
            
if __name__ == '__main__' : main()
