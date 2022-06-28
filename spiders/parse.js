function uuidv4(){
    return "{xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx}".replace(/[xy]/g, function(t) {
            var e = 16 * Math.random() | 0;
            return ("x" == t ? e : 3 & e | 8).toString(16)
        })
}

function uuid() {
    for (var G = [], Q = 0; Q < 36; Q++)
        G[Q] = "0123456789abcdef".substr(Math.floor(16 * Math.random()), 1);
    return G[14] = "4",
    G[19] = "0123456789abcdef".substr(3 & G[19] | 8, 1),
    G[8] = G[13] = G[18] = G[23] = "-",
    G.join("")
}

function he(G){
    return btoa(G).substring(0, 64);
}