
typedef i32 int
struct Vertex {
    1: double mapId,
    2: int zoneId,
    3: optional bool onlyDirections
}
struct Server {
    1: int id,
    2: int status,
    3: int completion,
    4: int charactersCount,
    5: int charactersSlots,
    6: double date,
    7: bool isMonoAccount,
    8: bool isSelectable,
}
enum SessionType {
    FIGHT = 0,
    FARM = 1,
}
enum PathType {
    RandomSubAreaFarmPath = 0,
    CyclicFarmPath = 1,
}
struct Path {
    1: string id,
    2: PathType type,
    3: optional Vertex startVertex,
}
struct Spell {
    1:int id,
    2:string name
}
struct Character {
    1:string name,
    2:double id,
    3:int level,
    4:int breedId,
    5:string breedName,
    6:int serverId,
    7:string serverName
}
struct Session {
    1: double id,
    3: Character leader,
    4: optional list<Character> followers,
    5: optional Character seller,
    6: SessionType type,
}
exception DofusError {
    1: int code,
    2: string message
}
service Pyd2botService {
    list<Character> fetchCharacters(1: string token, 2: int serverId) throws (1: DofusError error),
    list<Server> fetchUsedServers(1: string token) throws (1: DofusError error),
    void runSession(1: string token, 6:Session session) throws (1: DofusError error),
    list<Spell> fetchBreedSpells(1: int breedId) throws (1: DofusError error),
    string fetchJobsInfosJson() throws (1: DofusError error),
}
       
    