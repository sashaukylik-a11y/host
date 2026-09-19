//go:build windows

package main

import (
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"runtime"
	"syscall"
	"time"
	"unsafe"
)

const (
	WS_OVERLAPPEDWINDOW=0x00CF0000; WS_VISIBLE=0x10000000
	WM_DESTROY=0x0002; WM_CLOSE=0x0010; WM_LBUTTONDOWN=0x0201; WM_KILLFOCUS=0x0008
	PM_REMOVE=1; SW_SHOW=5; IDC_ARROW=32512; SRCCOPY=0x00CC0020; DIB_RGB_COLORS=0
)
var (
	u32=syscall.NewLazyDLL("user32.dll"); g32=syscall.NewLazyDLL("gdi32.dll"); k32=syscall.NewLazyDLL("kernel32.dll")
	reg=u32.NewProc("RegisterClassExW"); create=u32.NewProc("CreateWindowExW"); def=u32.NewProc("DefWindowProcW")
	show=u32.NewProc("ShowWindow"); upd=u32.NewProc("UpdateWindow"); peek=u32.NewProc("PeekMessageW")
	trans=u32.NewProc("TranslateMessage"); disp=u32.NewProc("DispatchMessageW"); quit=u32.NewProc("PostQuitMessage")
	cursor=u32.NewProc("LoadCursorW"); getkey=u32.NewProc("GetAsyncKeyState"); getcur=u32.NewProc("GetCursorPos")
	setcur=u32.NewProc("SetCursorPos"); client2screen=u32.NewProc("ClientToScreen"); showcur=u32.NewProc("ShowCursor")
	focus=u32.NewProc("GetForegroundWindow"); getdc=u32.NewProc("GetDC"); releasedc=u32.NewProc("ReleaseDC")
	mod=k32.NewProc("GetModuleHandleW"); stretch=g32.NewProc("StretchDIBits")
)
type WC struct{ Sz,Style uint32; Proc uintptr; C1,C2 int32; Inst,Icon,Cursor,Bg syscall.Handle; Menu,Name *uint16; IconSm syscall.Handle }
type Pt struct{ X,Y int32 }; type Msg struct{ H syscall.Handle; M uint32; W,L uintptr; T uint32; P Pt; Pr uint32 }
type BIH struct{ Size uint32; W,H int32; Planes,Bit uint16; Comp,SizeImage uint32; XP,YP int32; Used,Important uint32 }
type BMI struct{ H BIH; Colors [3]uint32 }
type Vec struct{ X,Y float64 }
type Enemy struct{ P Vec; HP int; Alive bool }
type Save struct{ Sens float64; Invert bool; Best float64; Wins int }
type Game struct{
	h syscall.Handle; dc syscall.Handle; w,hgt int; pix []uint32; running,locked bool
	x,y,a,pitch float64; hp,ammo,reserve int; weapon int; objective int; power,flash,key bool; modules int
	enemies []Enemy; keysPrev map[int]bool; save Save; start time.Time; note string; noteT float64
}

var G *Game
var world=[]string{
"11111111111111111111111111111111",
"10000000000000000000000000000001",
"10111101111101111111101111111001",
"10000100000100000000100000001001",
"11100101110111101110101111101001",
"10000100010000001000100000101001",
"10111111010111111011111110101001",
"10000000010000000000000000100001",
"10111111111101111111111110111101",
"10000000000101000000000010000001",
"11111101110101011111111011111001",
"10000101000101010000001000001001",
"10110101011101010111101111101001",
"10010100010001010000100000101001",
"11010111110111011110111110101001",
"10010000000100000010000000100001",
"10111111110101111010111111111101",
"10000000010100001010000000000001",
"10111111010111101011111111111001",
"10000001010000101000000000001001",
"11111001011110101111111111101001",
"10000001000000100000000000101001",
"10111111111111111111111110101001",
"10000000000000000000000000100001",
"10111111111111101111111111111101",
"10000000000000100000000000000001",
"11111111111110101111111111111001",
"10000000000000100000000000001001",
"10111111111111111111111111101001",
"10000000000000000000000000000001",
"10000000000000000000000000000001",
"11111111111111111111111111111111",
}
func U(s string)*uint16{p,_:=syscall.UTF16PtrFromString(s);return p}
func down(k int)bool{r,_,_:=getkey.Call(uintptr(k));return int16(r&0xffff)<0}
func press(g *Game,k int)bool{d:=down(k); p:=g.keysPrev[k]; g.keysPrev[k]=d; return d&&!p}
func clamp(v,a,b float64)float64{if v<a{return a};if v>b{return b};return v}
func wall(x,y float64)bool{ix,iy:=int(x),int(y);if iy<0||iy>=len(world)||ix<0||ix>=len(world[iy]){return true};return world[iy][ix]=='1'}
func proc(hwnd syscall.Handle,m uint32,w,l uintptr)uintptr{
	switch m{
	case WM_DESTROY: if G!=nil{G.running=false};quit.Call(0);return 0
	case WM_CLOSE: u32.NewProc("DestroyWindow").Call(uintptr(hwnd));return 0
	case WM_KILLFOCUS: if G!=nil{G.unlock()}
	case WM_LBUTTONDOWN: if G!=nil{if !G.locked{G.lock()}else{G.shoot()}}
	}
	r,_,_:=def.Call(uintptr(hwnd),uintptr(m),w,l);return r
}
func (g *Game) lock(){if g.locked{return};g.locked=true;for{r,_,_:=showcur.Call(0);if int32(r)<0{break}}}
func (g *Game) unlock(){if !g.locked{return};g.locked=false;for{r,_,_:=showcur.Call(1);if int32(r)>=0{break}}}
func (g *Game) center()(int32,int32){p:=Pt{int32(g.w/2),int32(g.hgt/2)};client2screen.Call(uintptr(g.h),uintptr(unsafe.Pointer(&p)));return p.X,p.Y}
func (g *Game) mouse(){
	if !g.locked{return};fg,_,_:=focus.Call();if syscall.Handle(fg)!=g.h{return}
	var p Pt;getcur.Call(uintptr(unsafe.Pointer(&p)));cx,cy:=g.center();dx,dy:=float64(p.X-cx),float64(p.Y-cy)
	g.a+=dx*g.save.Sens*0.0024
	sign:=1.0;if g.save.Invert{sign=-1};g.pitch=clamp(g.pitch-dy*g.save.Sens*0.0018*sign,-0.72,0.72)
	setcur.Call(uintptr(cx),uintptr(cy))
}
func (g *Game) savePath()string{d:=filepath.Join(os.Getenv("LOCALAPPDATA"),"NEON_RIFT","data");os.MkdirAll(d,0755);return filepath.Join(d,"state.json")}
func (g *Game) load(){g.save=Save{Sens:1};if b,e:=os.ReadFile(g.savePath());e==nil{json.Unmarshal(b,&g.save)};if g.save.Sens<=0{g.save.Sens=1}}
func (g *Game) saveNow(){b,_:=json.MarshalIndent(g.save,"","  ");os.WriteFile(g.savePath(),b,0644)}
func objective(n int)string{
	s:=[]string{"НАЙДИТЕ ФОНАРИК","НАЙДИТЕ ПРЕДОХРАНИТЕЛЬ","ВОССТАНОВИТЕ ПИТАНИЕ","ДОБЕРИТЕСЬ ДО СКЛАДА","ВОЗЬМИТЕ ПИСТОЛЕТ","НАЙДИТЕ КЛЮЧ-КАРТУ","ПРОЙДИТЕ В ЛАБОРАТОРИЮ","НАЙДИТЕ ДВА ЭНЕРГОМОДУЛЯ","ЗАПУСТИТЕ ГЕНЕРАТОР","ВЫЙДИТЕ ВО ДВОР","АКТИВИРУЙТЕ ВОРОТА","ПЕРЕЖИВИТЕ АТАКУ","ВЫБЕРИТЕСЬ ИЗ КОМПЛЕКСА"}
	if n<0||n>=len(s){return ""};return s[n]
}
func (g *Game) init(){
	g.x,g.y=2.5,2.5;g.a=0;g.hp=100;g.ammo=0;g.reserve=0;g.weapon=0;g.objective=0;g.start=time.Now()
	g.enemies=[]Enemy{{Vec{8.5,3.5},70,true},{Vec{13.5,7.5},70,true},{Vec{18.5,9.5},90,true},{Vec{23.5,13.5},90,true},{Vec{25.5,20.5},110,true},{Vec{8.5,25.5},110,true}}
	g.note="Вы приходите в себя в заброшенном комплексе.";g.noteT=5
}
func near(a,b Vec,r float64)bool{return math.Hypot(a.X-b.X,a.Y-b.Y)<r}
func (g *Game) interact(){
	p:=Vec{g.x,g.y}
	switch g.objective{
	case 0: if near(p,Vec{4.5,2.5},1.4){g.flash=true;g.objective++;g.note="Фонарик найден. Найдите предохранитель.";g.noteT=4}
	case 1: if near(p,Vec{6.5,3.5},1.4){g.objective++;g.note="Предохранитель найден.";g.noteT=3}
	case 2: if near(p,Vec{8.5,5.5},1.5){g.power=true;g.objective++;g.note="Питание восстановлено. Двери разблокированы.";g.noteT=4}
	case 3: if g.x>10{g.objective++;g.note="Склад. Найдите оружие.";g.noteT=3}
	case 4: if near(p,Vec{12.5,7.5},1.5){g.weapon=1;g.ammo=12;g.reserve=48;g.objective++;g.note="Пистолет получен. R — перезарядка.";g.noteT=4}
	case 5: if near(p,Vec{15.5,11.5},1.6){g.key=true;g.objective++;g.note="Ключ-карта найдена.";g.noteT=3}
	case 6: if g.x>18&&g.y>12{g.objective++;g.note="Лаборатория. Найдите энергомодули.";g.noteT=4}
	case 7:
		if near(p,Vec{21.5,17.5},1.5)&&g.modules<1{g.modules=1;g.note="Энергомодуль 1/2";g.noteT=3}
		if near(p,Vec{26.5,18.5},1.5)&&g.modules==1{g.modules=2;g.objective++;g.note="Энергомодули 2/2";g.noteT=3}
	case 8: if near(p,Vec{27.5,22.5},1.7)&&g.modules==2{g.objective++;g.note="Генератор запущен. Идите во двор.";g.noteT=4}
	case 9: if g.y>24{g.objective++;g.note="Внешний двор. Найдите панель ворот.";g.noteT=4}
	case 10: if near(p,Vec{28.5,28.5},2){g.objective++;g.note="Ворота открываются. Переживите атаку!";g.noteT=5}
	case 12: if g.y>29.2{g.win()}
	}
}
func (g *Game) reload(){if g.weapon==0{return};cap:=12;if g.weapon==2{cap=30};need:=cap-g.ammo;if need>g.reserve{need=g.reserve};g.ammo+=need;g.reserve-=need}
func rayWall(x,y,a,max float64)float64{for d:=0.05;d<max;d+=0.05{if wall(x+math.Cos(a)*d,y+math.Sin(a)*d){return d}};return max}
func adiff(a,b float64)float64{d:=math.Mod(a-b+math.Pi,2*math.Pi)-math.Pi;return math.Abs(d)}
func (g *Game) shoot(){
	if !g.locked||g.weapon==0||g.ammo<=0{return};g.ammo--;limit:=rayWall(g.x,g.y,g.a,30);best:=-1;bd:=limit
	for i:=range g.enemies{e:=&g.enemies[i];if !e.Alive{continue};ang:=math.Atan2(e.P.Y-g.y,e.P.X-g.x);d:=math.Hypot(e.P.X-g.x,e.P.Y-g.y);if d<bd&&adiff(ang,g.a)<0.055{best=i;bd=d}}
	if best>=0{g.enemies[best].HP-=35;if g.enemies[best].HP<=0{g.enemies[best].Alive=false}}
}
func (g *Game) enemiesUpdate(dt float64){
	for i:=range g.enemies{e:=&g.enemies[i];if !e.Alive{continue};d:=math.Hypot(e.P.X-g.x,e.P.Y-g.y);if d<9&&d>1.2{vx:=(g.x-e.P.X)/d*dt*1.1;vy:=(g.y-e.P.Y)/d*dt*1.1;if !wall(e.P.X+vx,e.P.Y){e.P.X+=vx};if !wall(e.P.X,e.P.Y+vy){e.P.Y+=vy}};if d<1.35{g.hp-=int(18*dt);if g.hp<=0{g.lose();return}}}
	if g.objective==11{alive:=0;for _,e:=range g.enemies{if e.Alive{alive++}};if alive==0{g.objective=12;g.note="Путь свободен. Выбирайтесь!";g.noteT=5}}
}
func (g *Game) update(dt float64){
	g.mouse();if press(g,0x1B){if g.locked{g.unlock()}else{g.lock()}}
	if press(g,'E'){g.interact()};if press(g,'R'){g.reload()};if press(g,0x71){g.save.Sens=clamp(g.save.Sens-.1,.2,2.5);g.saveNow()};if press(g,0x72){g.save.Sens=clamp(g.save.Sens+.1,.2,2.5);g.saveNow()};if press(g,0x73){g.save.Invert=!g.save.Invert;g.saveNow()}
	if g.locked{
		sp:=2.7;if down(0x10){sp=4.7};mx,my:=0.0,0.0
		if down('W'){mx+=math.Cos(g.a);my+=math.Sin(g.a)};if down('S'){mx-=math.Cos(g.a);my-=math.Sin(g.a)}
		if down('A'){mx+=math.Cos(g.a-math.Pi/2);my+=math.Sin(g.a-math.Pi/2)};if down('D'){mx+=math.Cos(g.a+math.Pi/2);my+=math.Sin(g.a+math.Pi/2)}
		l:=math.Hypot(mx,my);if l>0{mx,my=mx/l*sp*dt,my/l*sp*dt;if !wall(g.x+mx,g.y){g.x+=mx};if !wall(g.x,g.y+my){g.y+=my}}
	}
	if g.objective==3&&g.x>10{g.interact()};if g.objective==6&&g.x>18&&g.y>12{g.interact()};if g.objective==9&&g.y>24{g.interact()}
	g.enemiesUpdate(dt);if g.noteT>0{g.noteT-=dt}
}
func rgb(r,g,b uint8)uint32{return uint32(b)<<16|uint32(g)<<8|uint32(r)}
func (g *Game) clear(c uint32){for i:=range g.pix{g.pix[i]=c}}
func (g *Game) rect(x0,y0,x1,y1 int,c uint32){if x0<0{x0=0};if y0<0{y0=0};if x1>g.w{x1=g.w};if y1>g.hgt{y1=g.hgt};for y:=y0;y<y1;y++{o:=y*g.w;for x:=x0;x<x1;x++{g.pix[o+x]=c}}}
func (g *Game) render(){
	if g.w<320||g.hgt<200{return};g.clear(rgb(26,29,34));half:=g.hgt/2+int(g.pitch*180)
	g.rect(0,0,g.w,half,rgb(23,26,31));g.rect(0,half,g.w,g.hgt,rgb(38,39,40))
	fov:=1.05
	zbuf:=make([]float64,g.w)
	for sx:=0;sx<g.w;sx+=2{ra:=g.a+(float64(sx)/float64(g.w)-.5)*fov;d:=rayWall(g.x,g.y,ra,40);zbuf[sx]=d;correct:=d*math.Cos(ra-g.a);hh:=int(float64(g.hgt)/math.Max(.2,correct)*.55);y0:=half-hh/2;y1:=half+hh/2;shade:=uint8(clamp(210-correct*5,45,210));c:=rgb(shade,shade,uint8(float64(shade)*.95));g.rect(sx,y0,sx+2,y1,c)}
	for _,e:=range g.enemies{if !e.Alive{continue};dx,dy:=e.P.X-g.x,e.P.Y-g.y;d:=math.Hypot(dx,dy);ang:=math.Atan2(dy,dx);rel:=math.Mod(ang-g.a+math.Pi,2*math.Pi)-math.Pi;if math.Abs(rel)>fov*.58{continue};cx:=int((rel/fov+.5)*float64(g.w));sz:=int(float64(g.hgt)/math.Max(.3,d)*.45);if cx>=0&&cx<g.w&&d<zbuf[clampInt(cx-(cx%2),0,g.w-1)]{g.rect(cx-sz/3,half-sz/2,cx+sz/3,half+sz/2,rgb(180,45,38));g.rect(cx-sz/5,half-sz/2-sz/4,cx+sz/5,half-sz/2,rgb(60,65,72))}}
	cx,cy:=g.w/2,g.hgt/2;g.rect(cx-9,cy-1,cx+10,cy+2,rgb(235,235,235));g.rect(cx-1,cy-9,cx+2,cy+10,rgb(235,235,235))
	g.rect(0,0,g.w,34,rgb(8,11,16));g.rect(0,g.hgt-30,g.w,g.hgt,rgb(8,11,16))
	g.text(12,8,fmt.Sprintf("HP %03d   AMMO %02d/%03d   %s",g.hp,g.ammo,g.reserve,objective(g.objective)),rgb(235,240,245))
	g.text(12,g.hgt-23,fmt.Sprintf("WASD • LMB fire • E interact • R reload • F2/F3 sensitivity %.1f • F4 invert %v • MonoSystem",g.save.Sens,g.save.Invert),rgb(135,160,180))
	if g.noteT>0{g.text(20,52,g.note,rgb(255,205,95))}
	if !g.locked{g.text(g.w/2-135,g.hgt/2+45,"CLICK TO CAPTURE MOUSE",rgb(245,245,245))}
	bmi:=BMI{H:BIH{Size:uint32(unsafe.Sizeof(BIH{})),W:int32(g.w),H:-int32(g.hgt),Planes:1,Bit:32}}
	stretch.Call(uintptr(g.dc),0,0,uintptr(g.w),uintptr(g.hgt),0,0,uintptr(g.w),uintptr(g.hgt),uintptr(unsafe.Pointer(&g.pix[0])),uintptr(unsafe.Pointer(&bmi)),DIB_RGB_COLORS,SRCCOPY)
}
func clampInt(v,a,b int)int{if v<a{return a};if v>b{return b};return v}
func (g *Game) text(x,y int,s string,c uint32){
	// TextOutW on the same window DC; drawn after framebuffer blit on next frame, so use direct call immediately after render via overlay.
	// Kept compact: actual overlay call is in blitOverlay.
	g.overlay=append(g.overlay,ov{x,y,s,c})
}
type ov struct{x,y int;s string;c uint32}
var textout=g32.NewProc("TextOutW");var settext=g32.NewProc("SetTextColor");var setbk=g32.NewProc("SetBkMode")
func (g *Game) blitOverlay(){for _,o:=range g.overlay{setbk.Call(uintptr(g.dc),1);settext.Call(uintptr(g.dc),uintptr(o.c));p:=U(o.s);textout.Call(uintptr(g.dc),uintptr(o.x),uintptr(o.y),uintptr(unsafe.Pointer(p)),uintptr(len([]rune(o.s))))};g.overlay=g.overlay[:0]}
func (g *Game) win(){g.unlock();g.save.Wins++;elapsed:=time.Since(g.start).Seconds();if g.save.Best==0||elapsed<g.save.Best{g.save.Best=elapsed};g.saveNow();syscall.NewLazyDLL("user32.dll").NewProc("MessageBoxW").Call(uintptr(g.h),uintptr(unsafe.Pointer(U("Вы выбрались из комплекса!\n\nNEON RIFT — MonoSystem"))),uintptr(unsafe.Pointer(U("ESCAPED"))),0x40);u32.NewProc("DestroyWindow").Call(uintptr(g.h))}
func (g *Game) lose(){g.unlock();syscall.NewLazyDLL("user32.dll").NewProc("MessageBoxW").Call(uintptr(g.h),uintptr(unsafe.Pointer(U("Система костюма отключена. Попробуйте снова."))),uintptr(unsafe.Pointer(U("NEON RIFT"))),0x10);u32.NewProc("DestroyWindow").Call(uintptr(g.h))}
func (g *Game) makeWindow()error{
	runtime.LockOSThread();inst,_,_:=mod.Call();cur,_,_:=cursor.Call(0,IDC_ARROW);name:=U("MonoSystemNeonRiftRay")
	wc:=WC{Sz:uint32(unsafe.Sizeof(WC{})),Proc:syscall.NewCallback(proc),Inst:syscall.Handle(inst),Cursor:syscall.Handle(cur),Name:name}
	if r,_,e:=reg.Call(uintptr(unsafe.Pointer(&wc)));r==0{return e}
	g.w,g.hgt=1280,720;r,_,e:=create.Call(0,uintptr(unsafe.Pointer(name)),uintptr(unsafe.Pointer(U("NEON RIFT: ABANDONED — MonoSystem"))),WS_OVERLAPPEDWINDOW|WS_VISIBLE,120,80,uintptr(g.w),uintptr(g.hgt),0,0,inst,0);if r==0{return e}
	g.h=syscall.Handle(r);d,_,_:=getdc.Call(uintptr(g.h));g.dc=syscall.Handle(d);g.pix=make([]uint32,g.w*g.hgt);show.Call(uintptr(g.h),SW_SHOW);upd.Call(uintptr(g.h));return nil
}
func (g *Game) loop(){g.running=true;last:=time.Now();var m Msg;for g.running{for{r,_,_:=peek.Call(uintptr(unsafe.Pointer(&m)),0,0,0,PM_REMOVE);if r==0{break};trans.Call(uintptr(unsafe.Pointer(&m)));disp.Call(uintptr(unsafe.Pointer(&m))};now:=time.Now();dt:=now.Sub(last).Seconds();last=now;if dt>.05{dt=.05};g.update(dt);g.render();g.blitOverlay();time.Sleep(4*time.Millisecond)}}
func main(){g:=&Game{keysPrev:map[int]bool{}};G=g;g.load();if e:=g.makeWindow();e!=nil{return};defer releasedc.Call(uintptr(g.h),uintptr(g.dc));g.init();g.loop()}
