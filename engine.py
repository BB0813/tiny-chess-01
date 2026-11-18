import json,os,urllib.request as q
import base64 as b
from itertools import count
from collections import namedtuple

piece={"P":100,"N":280,"B":320,"R":479,"Q":929,"K":60000}
z=lambda s:[x-128 for x in b.b85decode(s)]
pst={"P":z("fPjF2fPjF2&ePV(=F-*Lhn<zIsGqEdZ;*bEj)0GIW`l}}hJk=-YKet)c7B6xVTgHKTyle9fPjF2fPjF2"),"N":z("K1($<c1cD$eR||vguZ-oio=1*$(z1@n3%1lp{bdXe}$iwmZO4zZi<bTl8=jWX>o#pf`DmkHfd&PZCz?R"),"B":z("MKUflX%$;eb(Eu4S)YPxcc);fw04|wnUR#DnwgJ^jf#<%k&u9gj+vN`h?$g+laz~whlZ4pd4h3ta&dNc"),"R":z("qn)9IrJ=a8x1G4dx4xphlcSuWt(%#TfQ68al6-f1WL<D;b7N9sR%BLZXI*AeOIl%OV^vg3VrXuKer{o4"),"Q":z("hJkn(#hBQdj-b4Dl+3x9eygCo$iJ(CfpC_QnUr&Sa&dlpe|BtYVtR9RaCLBHTyB7EadB%}Sz=*xVO(BT"),"K":z("gto689lX;*V2Zc6xVMUfLX1bOJ)EUsNwSN4ZH<6WNmWc_O;LDGQC3wkKwx8Fe1mdMM{bRTk)C~WhJUD%")}
for k,table in pst.items():
    rows=[(0,)+tuple(x+piece[k] for x in table[i:i+8])+(0,) for i in range(0,64,8)]
    pst[k]=(0,)*20+sum(rows,())+(0,)*20
K=[pst["K"],[60070-10*(abs(2*(i//10)-11)+abs(2*(i%10)-9)) for i in range(120)]]
NODE_CAP=90000
A1,H1,A8,H8=91,98,21,28
N,E,S,W=-10,1,10,-1
directions={"P":(N,N+N,N+W,N+E),"N":(N+N+E,E+N+E,E+S+E,S+S+E,S+S+W,W+S+W,W+N+W,N+N+W),"B":(N+E,S+E,S+W,N+W),"R":(N,E,S,W),"Q":(N,E,S,W,N+E,S+E,S+W,N+W),"K":(N,E,S,W,N+E,S+E,S+W,N+W)}
class Position(namedtuple("Position","board score wc bc ep kp")):
    def gen_moves(self):
        for i,p in enumerate(self.board):
            if p not in "PNBRQK":continue
            for d in directions[p]:
                for j in count(i+d,d):
                    q=self.board[j]
                    if q in " \nPNBRQK":break
                    if p=="P":
                        if d in (N,N+N) and q!=".":break
                        if d==N+N and (i<A1+N or self.board[i+N]!="."):break
                        if d in (N+W,N+E) and q=="." and j not in (self.ep,self.kp,self.kp-1,self.kp+1):break
                        if A8<=j<=H8:
                            for prom in "NBRQ":yield i,j,prom
                            break
                    yield i,j,""
                    if p in "PNK" or q in "pnbrqk":break
                    if i==A1 and self.board[j+E]=="K" and self.wc[0]:yield j+E,j+W,""
                    if i==H1 and self.board[j+W]=="K" and self.wc[1]:yield j+W,j+E,""
    def rotate(self,nullmove=False):
        return Position(self.board[::-1].swapcase(),-self.score,self.bc,self.wc,119-self.ep if self.ep and not nullmove else 0,119-self.kp if self.kp and not nullmove else 0)
    def move(self,move):
        i,j,prom=move
        p,q=self.board[i],self.board[j]
        put=lambda board,i,p:board[:i]+p+board[i+1:]
        board=self.board
        wc,bc,ep,kp=self.wc,self.bc,0,0
        score=self.score+self.value(move)
        board=put(board,j,board[i]);board=put(board,i,'.')
        wc=(wc[0] and i!=A1,wc[1] and i!=H1)
        bc=(bc[0] and j!=H8,bc[1] and j!=A8)
        if p=="K":
            wc=(False,False)
            if abs(j-i)==2:
                kp=(i+j)//2;r=A1 if j<i else H1
                board=put(board,r,'.');board=put(board,kp,'R')
        if p=="P":
            if A8<=j<=H8:board=put(board,j,prom)
            if j-i==2*N:ep=i+N
            if j==self.ep:board=put(board,j+S,'.')
        return Position(board[::-1].swapcase(),-score,bc,wc,119-ep if ep else 0,119-kp if kp else 0)
    def value(self,move):
        i,j,prom=move;p,q=self.board[i],self.board[j]
        score=pst[p][j]-pst[p][i]
        if q in "pnbrqk":score+=pst[q.upper()][119-j]
        if abs(j-self.kp)<2:score+=pst["K"][119-j]
        if p=="K" and abs(i-j)==2:
            score+=pst["R"][(i+j)//2];score-=pst["R"][A1 if j<i else H1]
        if p=="P":
            if A8<=j<=H8:score+=pst[prom][j]-pst["P"][j]
            if j==self.ep:score+=pst["P"][119-(j+S)]
        return score
    def king_capture(self):
        return next((m for m in self.gen_moves() if self.board[m[1]]=="k" or abs(m[1]-self.kp)<2),None)

class Stop(Exception):pass
class Searcher:
    def __init__(self):
        self.tp_score,self.tp_move,self.history={},{},set()
        self.nodes=0;self.node_cap=NODE_CAP
    def bound(self,pos,gamma,depth,root=False):
        self.nodes+=1
        if self.nodes>self.node_cap:raise Stop
        depth=max(depth,0)
        if pos.score<=-47923:return -69290
        if not root:
            entry=self.tp_score.get((pos,depth),(-69290,69290))
            if entry[0]>=gamma:return entry[0]
            if entry[1]<gamma:return entry[1]
            if depth>0 and pos in self.history:return 0
        def moves():
            killer=self.tp_move.get(pos)
            if not root and depth>2 and abs(pos.score)<500 and any(c in pos.board for c in "RBNQ"):
                score=-self.bound(pos.rotate(True),1-gamma,depth-3)
                proof=score>=gamma and (self.tp_move.get(pos) or pos.king_capture())
                if proof and pos.value(proof)>=47923:yield proof,69290
                elif score<gamma or self.bound(pos.rotate(True),1-47923,depth-3)>=1-47923:yield None,score
            if depth==0:yield None,pos.score
            if not killer and depth>2:
                self.bound(pos,gamma,depth-3,True);killer=self.tp_move.get(pos)
            if killer and pos.value(killer)>=40-depth*140:
                yield killer,-self.bound(pos.move(killer),1-gamma,depth-1)
            for cnt,(val,move) in enumerate(sorted(((v,m) for m in pos.gen_moves() if (v:=pos.value(m))>=40-depth*140),reverse=True)):
                if depth<=1 and pos.score+val<gamma:
                    yield (move,69290) if val>=47923 else (None,pos.score+val)
                    break
                red=depth>2 and cnt>2 and val<60
                score=-self.bound(pos.move(move),1-gamma,depth-2 if red else depth-1)
                if red and score>=gamma:score=-self.bound(pos.move(move),1-gamma,depth-1)
                yield move,score
        best,live=-69290,False
        for move,score in moves():
            best=max(best,score);live |= move is not None and score>-69290
            if best>=gamma:
                if move is not None and depth:
                    self.tp_move[pos]=move
                break
        if depth and not live and all(pos.move(m).king_capture() for m in pos.gen_moves()):
            best=-47923 if pos.rotate(True).king_capture() else 0
        if not root:
            self.tp_score[pos,depth]=(best,entry[1]) if best>=gamma else (entry[0],best)
        return best
    def search(self,history):
        self.nodes,self.history=0,set(history)
        pos=history[-1]
        pst["K"]=K[sum(c.isupper() for c in pos.board)==1 or sum(c.islower() for c in pos.board)==1]
        gamma=0
        for depth in range(1,1000):
            lower,upper,probes=1-69290,69290,0
            while lower<upper-15:
                score=self.bound(pos,gamma,depth,True)
                if score>=gamma:lower=max(lower,score)
                else:upper=min(upper,score)
                probes+=1
                yield depth,gamma,score,self.tp_move.get(pos)
                if lower>upper or probes>40:break
                gamma=(lower+upper+1)//2

def parse(c):return A1+ord(c[0])-ord('a')-10*(int(c[1])-1)
def render(i):return chr((i-A1)%10+ord('a'))+str(1-(i-A1)//10)
def from_board(board,wc=(True,True),bc=(True,True),ep=0,kp=0):
    score=sum(pst[p][i] if p.isupper() else -pst[p.upper()][119-i] for i,p in enumerate(board) if p.isalpha())
    return Position(board,score,wc,bc,ep,kp)

def fen_to_state(fen):
    f=fen.split()
    c=f[2] if len(f)>2 else ""
    rows=["         \n"]*2+[" "+"".join("."*int(x) if x.isdigit() else x for x in row)+"\n" for row in f[0].split("/")]+["         \n"]*2
    b="".join(rows)
    ep=parse(f[3]) if len(f)>3 and f[3]!="-" else 0
    wc=("Q"in c,"K"in c)
    bc=("q"in c,"k"in c)
    return b,ep,wc,bc

def choose_move(g):
    ms=g.get("moves")or[]
    sf=g.get("start_fen")or g["fen"]
    z=sf.split()[1]=="b"
    b,e,w,c=fen_to_state(sf);p=from_board(b,w,c,e)
    if z:p=p.rotate()
    h=[p]
    for k,u in enumerate(ms):
        i,j=parse(u[:2]),parse(u[2:])
        if (k+z)%2:i,j=119-i,119-j
        if p.board[i].isupper():p=p.move((i,j,u[4:5].upper()))
        h.append(p)
    def out(m):
        i,j,pm=m
        if z^(len(ms)%2):i,j=119-i,119-j
        return render(i)+render(j)+pm.lower()
    s=Searcher();best=""
    try:
        for _,_,_,m in s.search(h):
            if m is not None:best=out(m)
    except Stop:pass
    legal=g.get("legal_moves") or []
    if best and (not legal or best in legal):return best
    ms=[m for m in h[-1].gen_moves() if not legal or out(m) in legal]
    return out(max(ms,key=h[-1].value)) if ms else best

def main():
    u=os.environ.get("MAKEFUN_ENV_URL")
    if not u:return
    u=u.rstrip("/")
    while 1:
        with q.urlopen(q.Request(u+"/game",data=b"{}",headers={"Content-Type":"application/json"})) as r:g=json.load(r)
        if g.get("status")=="done":break
        while g.get("status")=="your_move":
            with q.urlopen(q.Request(u+"/move",data=json.dumps({"game":g["game"],"move":choose_move(g)}).encode(),headers={"Content-Type":"application/json"})) as r:g=json.load(r)

if __name__=="__main__":main()
