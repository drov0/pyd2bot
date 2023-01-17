
typedef i32 int 
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
exception DofusError {
    1: int code,
    2: string message
}
service Pyd2botService {
    list<Character> fetchCharacters(1: string token, 2: int serverId) throws (1: DofusError error),
    string fetchUsedServers(1: string token) throws (1: DofusError error),
    void runSession(1: string token, 6:string sessionJson) throws (1: DofusError error),
    list<Spell> fetchBreedSpells(1: int breedId) throws (1: DofusError error),
    string fetchJobsInfosJson() throws (1: DofusError error),
    void moveToVertex(1: string vertex),
    void followTransition(1: string transition),
    string getStatus() throws (1: DofusError error),
    void comeToBankToCollectResources(1: string bankInfos, 3: string guestInfos) throws (1: DofusError error),
    string getCurrentVertex() throws (1: DofusError error),
    int getInventoryKamas() throws (1: DofusError error),
}
       
    