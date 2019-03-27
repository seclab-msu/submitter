package main

import (
    "io"
    "log"
    "time"
    "io/ioutil"
    "net/http"
    "math/big"
    "math/rand"
    "strconv"
    "strings"
    "crypto/md5"
)

const ttl = 5 * time.Second
const m = 899877779931337

const ngx404 = `<html>
<head><title>404 Not Found</title></head>
<body bgcolor="white">
<center><h1>404 Not Found</h1></center>
<hr><center>nginx/1.14.0 (Ubuntu)</center>
</body>
</html>
<!-- a padding to disable MSIE and Chrome friendly error page -->
<!-- a padding to disable MSIE and Chrome friendly error page -->
<!-- a padding to disable MSIE and Chrome friendly error page -->
<!-- a padding to disable MSIE and Chrome friendly error page -->
<!-- a padding to disable MSIE and Chrome friendly error page -->
<!-- a padding to disable MSIE and Chrome friendly error page -->
`

const letterBytes = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
const PNG = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x02\xc2\x00\x00\x00\xbb\x08\x02\x00\x00\x00\xe0"

var ngx404Bytes = []byte(ngx404)

var modulo = big.NewInt(m)

var dictionaryJS = []string{
    "js",
    "jquery",
    "scripts",
    "json",
    "javascript",
    "lib",
    "libs",
    "watch",
    "api",
    "src",
    "library",
    "code",
    "RANDOM",
    "VERSION",
}

var dictionaryPNG = []string{
    "images",
    "logo",
    "pic",
    "pictures",
    "icon",
    "icons",
    "img",
    "background",
    "fontface",
    "palette",
    "RANDOM",
}

func randomString(n int) string {
    b := make([]byte, n)
    for i := range b {
        b[i] = letterBytes[rand.Int63() % int64(len(letterBytes))]
    }
    return string(b)
}

type endpoint struct {
    data []byte
    ts time.Time
    dh int64
    enc bool
}

type endpointPutRequest struct {
    path string
    data []byte
    resp chan string
}

type endpointEncPutRequest struct {
    path string
    data []byte
    dh int64
    resp chan string
}

type endpointGetRequest struct {
    path string
    resp chan []byte
}

type endpointEncGetRequest struct {
    path string
    dh int64
    resp chan []byte
}

var (
    storage = map[string]endpoint{}
    puts = make(chan *endpointPutRequest, 1000)
    gets = make(chan *endpointGetRequest, 1000)
    encs = make(chan *endpointEncPutRequest, 1000)
    encgets = make(chan *endpointEncGetRequest, 1000)
)

func encrypt(data []byte, dha int64, dhB int64) []byte {
    a := big.NewInt(dha)
    B := big.NewInt(dhB)
    key := a.Exp(B, a, modulo).Bytes()
    blockIdx := 0
    stateIdx := 0
    state := md5.Sum(append([]byte(strconv.Itoa(blockIdx)), key...))
    for i := 0; i < len(data); i++ {
        if stateIdx > 15 {
            blockIdx += 1
            state = md5.Sum(
                append([]byte(strconv.Itoa(blockIdx)),
                    append(state[:], key...)...),
            )
            stateIdx = 0
        }
        data[i] = data[i] ^ state[stateIdx]
        stateIdx += 1
    }
    return data
}

func genRandomVersion() string {
    verLen := 2
    verParts := make([]string, 0, 3)
    if rand.Float64() > 0.5 {
        verLen = 3
    }
    for i := 0; i < verLen; i++ {
        verParts = append(verParts, strconv.Itoa(rand.Intn(10)))
    }
    return strings.Join(verParts, ".")
}

func randomName(enc bool) string {
    nameParts := make([]string, 0, 5)

    dictionary := dictionaryJS

    if enc {
        dictionary = dictionaryPNG
    }

    for {
        if len(nameParts) > 0 {
            if len(nameParts) > 5 || rand.Float64() > 0.7 {
                break
            }
        }
        part := dictionary[rand.Int63() % int64(len(dictionary))]
        if part == "RANDOM" {
            part = randomString(1 + rand.Intn(6))
        } else if part == "VERSION" {
            part = genRandomVersion()
        }
        nameParts = append(nameParts, part)
    }
    suffix := ".js"
    if enc {
        suffix = ".png"
    }
    return strings.Join(nameParts, "/") + suffix
}

func randomUniqueName(enc bool) string {
    name := randomName(enc)
    for _, ok := storage[name]; ok; _, ok = storage[name] {
        name = randomName(enc)
    }
    return name
}

func controller() {
    ticker := time.NewTicker(ttl).C
    for {
        select {
        case g := <- gets:
            ep, ok := storage[g.path]
            if !ok {
                g.resp <- nil
            } else {
                if ep.enc {
                    g.resp <- nil
                } else {
                    delete(storage, g.path)
                    g.resp <- ep.data
                }
            }
        case p := <- puts:
            path := p.path
            if path == "" {
                path = randomUniqueName(false)
            }
            storage[path] = endpoint{data: p.data, ts: time.Now()}
            p.resp <- path
        case en := <- encs:
            path := en.path
            if path == "" {
                path = randomUniqueName(true)
            }
            storage[path] = endpoint{
                data: en.data,
                ts: time.Now(),
                dh: en.dh,
                enc: true,
            }
            en.resp <- path
        case eng := <- encgets:
            encep, ok := storage[eng.path]
            if !ok {
                eng.resp <- nil
            } else {
                if !encep.enc {
                    eng.resp <- nil
                } else {
                    delete(storage, eng.path)
                    eng.resp <- encrypt(encep.data, encep.dh, eng.dh)
                }
            }
        case <- ticker:
            var oldEndpoints []string
            ts := time.Now()
            for path, ep := range storage {
                if ts.Sub(ep.ts) > ttl {
                    oldEndpoints = append(oldEndpoints, path)
                }
            }
            for _, path := range oldEndpoints {
                log.Printf("Clear %s", path)
                delete(storage, path)
            }
        }
    }
}

func storageGetter(w http.ResponseWriter, r *http.Request) {
    respCh := make(chan []byte)
    if len(r.URL.Path) < 2 {
        w.WriteHeader(404)
        w.Write(ngx404Bytes)
        return
    }
    path := r.URL.Path[1:]
    if r.Method == "GET" {
        gets <- &endpointGetRequest{
            path: path, resp: respCh,
        }
        log.Printf("Get regular %s", path)
        resp := <- respCh
        if resp == nil {
            w.WriteHeader(404)
            w.Write(ngx404Bytes)
            return
        }
        w.Write(resp)
    } else if r.Method == "POST" {
        log.Printf("Get enc %s", path)
        err := r.ParseMultipartForm(0)
        if err != nil {
            log.Printf("Error parsing multipar: %v", err)
            w.WriteHeader(404)
            w.Write(ngx404Bytes)
            return
        }
        dh, err := strconv.ParseInt(r.FormValue("n"), 10, 64)
        if err != nil {
            log.Printf("Error parsing int: %v", err)
            w.WriteHeader(404)
            w.Write(ngx404Bytes)
            return
        }
        encgets <- &endpointEncGetRequest{
            path: path, dh: dh, resp: respCh,
        }
        resp := <- respCh
        if resp == nil {
            w.WriteHeader(404)
            w.Write(ngx404Bytes)
            return
        }
        io.WriteString(w, PNG)
        w.Write(resp)
    }
}

func storageAdder(w http.ResponseWriter, r *http.Request) {
    body, err := ioutil.ReadAll(r.Body)
    if err != nil {
        panic(err)
    }
    respCh := make(chan string)
    query := r.URL.Query()
    aStr, ok := query["a"]
    enc := false
    if !ok {
        puts <- &endpointPutRequest{
            data: body, resp: respCh,
        }
    } else {
        enc = true
        a, err := strconv.ParseInt(aStr[0], 10, 64)
        if err != nil {
            panic(err)
        }
        encs <- &endpointEncPutRequest{
            data: body,
            dh: a,
            resp: respCh,
        }
    }
    name := <- respCh
    log.Printf("Added enc %t path %s", enc, name)
    w.Write([]byte(name))
}

func main() {
    rand.Seed(time.Now().UnixNano())
    mainServer := &http.Server{
        Addr:    "127.0.0.1:8080",
        Handler: http.HandlerFunc(storageGetter),
    }
    controlServer := &http.Server{
        Addr:    "127.0.0.1:4050",
        Handler: http.HandlerFunc(storageAdder),
    }
    go controller()
    go mainServer.ListenAndServe()
    go controlServer.ListenAndServe()
    select {}
}