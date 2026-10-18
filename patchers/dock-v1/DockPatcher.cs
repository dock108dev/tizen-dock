using Mono.Cecil;
using Mono.Cecil.Cil;
using System.Reflection.PortableExecutable;
using System.Text;
using System.Text.Json;
using System.Security.Cryptography;
var bytes=File.ReadAllBytes(args[0]);
using var asm=AssemblyDefinition.ReadAssembly(args[0]);
using var pe=new PEReader(new MemoryStream(bytes));
var methods=asm.MainModule.Types.SelectMany(t=>t.Methods).Where(m=>m.HasBody).ToArray();
var changed=new List<string>();
MethodDefinition M(string type,string name)=>methods.Single(m=>m.DeclaringType.Name==type && m.Name==name);
int FileOffset(int rva){var s=pe.PEHeaders.SectionHeaders.Single(s=>rva>=s.VirtualAddress&&rva<s.VirtualAddress+s.VirtualSize);return s.PointerToRawData+rva-s.VirtualAddress;}
int Start(MethodDefinition m){int o=FileOffset(m.RVA);return o+((bytes[o]&3)==2?1:(bytes[o+1]>>4)*4);}
void Patch(MethodDefinition m,byte[] code){
 int o=FileOffset(m.RVA),start=Start(m),capacity=start-o+m.Body.CodeSize;
 if(code.Length+1<=capacity && code.Length<64){bytes[o]=(byte)((code.Length<<2)|2);code.CopyTo(bytes,o+1);}
 else if(start-o>=12 && code.Length<=m.Body.CodeSize){bytes[o]=3;bytes[o+1]=0x30;BitConverter.GetBytes((ushort)8).CopyTo(bytes,o+2);BitConverter.GetBytes(code.Length).CopyTo(bytes,o+4);Array.Clear(bytes,o+8,4);code.CopyTo(bytes,o+12);}
 else throw new Exception("Body does not fit: "+m.FullName);
 changed.Add(m.FullName);
}
byte[] I(int n)=>n>=-1&&n<=8?new byte[]{(byte)(0x16+n),0x2a}:n>=-128&&n<=127?new byte[]{0x1f,(byte)n,0x2a}:new byte[]{0x20}.Concat(BitConverter.GetBytes(n)).Append((byte)0x2a).ToArray();
void Const(string t,string m,int value)=>Patch(M(t,m),I(value));
void Nop(string t,string m)=>Patch(M(t,m),new byte[]{0x2a});
foreach(var (name,value) in new[]{("COMMON_HEIGHT",22),("COMMON_NOCONTENT_HEIGHT",22),("ACCELERATOR_HEIGHT",0),("PARTIAL_CONTENT_HEIGHT",0),("CONTENTLAYER_HEIGHT",0),("LAUNCHER_WIDTH",168),("LAUNCHER_HEIGHT_FOCUSED",22),("LAUNCHER_HEIGHT_SELECTED",22),("LAUNCHER_TOP_Y_SELECTED",0)})Const("GUIDef","get_"+name,value);
Const("CurrentState","get_IsShowContent",0);
foreach(var name in new[]{"CheckFocusToAccelerator","FocusToAccelerator","FocusToContent","FocusToImmersiveBanner"})Const("ViewController",name,0);
Nop("ViewController","ContentStatusChange");
foreach(var name in new[]{"LoadContent","OnShow","ShowLoading"})Nop("ContentView",name);
Const("ContentView","IsFocusable",0);Const("ContentView","InitialLayerCount",0);
foreach(var name in new[]{"LoadAccelerator","OnShow"})Nop("AcceleratorView",name);

Const("AcceleratorView","CheckSetFocus",0);
Nop("ImmersiveBannerView","ShowImmersiveBanner");Const("ImmersiveBannerView","TrySetFocus",0);
// Keep the existing metadata table and all assembly identity intact. Reuse two
// unused-for-behavior diagnostic strings for the new absolute image paths.
uint ImageString(string methodName,string image){
 var ins=M("GUIDef",methodName).Body.Instructions.Single(i=>i.OpCode==OpCodes.Ldstr);
 // Use the long source-file string from a separate diagnostic method, leaving the resource name intact.
 var donorMethod=M(image.Contains("transparent")?"ViewController":"LauncherView",image.Contains("transparent")?"CreateBackground":"OnRelayout");
 var donor=donorMethod.Body.Instructions.First(i=>i.OpCode==OpCodes.Ldstr && i.Operand is string s && s.StartsWith("/home/abuild/"));
 int il=Start(donorMethod);
 uint token=BitConverter.ToUInt32(bytes,il+donor.Offset+1);
 int metadata=FileOffset(pe.PEHeaders.CorHeader!.MetadataDirectory.RelativeVirtualAddress);
 int vlen=BitConverter.ToInt32(bytes,metadata+12);int at=metadata+16+((vlen+3)&~3);int count=BitConverter.ToUInt16(bytes,at+2);at+=4;
 int us=-1;
 for(int j=0;j<count;j++){int offset=BitConverter.ToInt32(bytes,at);at+=8;int end=Array.IndexOf(bytes,(byte)0,at);string name=Encoding.ASCII.GetString(bytes,at,end-at);at=(end+4)&~3;if(name=="#US")us=metadata+offset;}
 if(us<0)throw new Exception("No string heap");
 int p=us+(int)(token&0xffffff);int oldFirst=bytes[p];int prefix=oldFirst<128?1:oldFirst<192?2:4;
 int oldLen=prefix==1?oldFirst:prefix==2?((oldFirst&63)<<8)|bytes[p+1]:throw new Exception("Unexpected string size");
 byte[] value=Encoding.Unicode.GetBytes(image);int length=value.Length+1;
 if(prefix!=2||length<128||length>=16384||length>oldLen)throw new Exception("Image path does not fit diagnostic string");
 bytes[p]=(byte)(0x80|(length>>8));bytes[p+1]=(byte)length;value.CopyTo(bytes,p+2);bytes[p+2+value.Length]=0;
 return token;
}
foreach(var (getter,image) in new[]{("get_EDEN_LAUNCHER_BG","compact-dock-background-v1.png"),("get_EDEN_COMMON_BG","compact-dock-transparent-v1.png")}){
 uint token=ImageString(getter,"/home/owner/share/tizen-dock/menu-overlay/"+image);
 Patch(M("GUIDef",getter),new byte[]{0x72}.Concat(BitConverter.GetBytes(token)).Append((byte)0x2a).ToArray());
}
// Style the strip and inset its contents twelve TV layout units. Preserve high contrast.
var allInstructions=methods.SelectMany(m=>m.Body.Instructions).ToArray();
uint Ref(string type,string name)=>allInstructions.Select(i=>i.Operand).OfType<MethodReference>().First(m=>m.DeclaringType.FullName==type&&m.Name==name).MetadataToken.ToUInt32();
var style=new List<byte>();
void Op(byte op,uint token){style.Add(op);style.AddRange(BitConverter.GetBytes(token));}
void Field(string name){style.Add(0x02);Op(0x7b,M("LauncherView","OnHighContrastChanged").DeclaringType.Fields.Single(f=>f.Name==name).MetadataToken.ToUInt32());}
Field("bgView");Op(0x6f,Ref("Tizen.NUI.BaseComponents.View","ClearBackground"));
Field("bgView");Op(0x28,M("GUIDef","get_EDEN_LAUNCHER_BG").MetadataToken.ToUInt32());Op(0x6f,Ref("Tizen.NUI.BaseComponents.View","set_BackgroundImage"));
Field("bgLayout");style.AddRange(new byte[]{0x1f,12});Op(0x6f,Ref("Tizen.TV.FLUX.FluxView","set_UnitPositionX"));style.Add(0x2a);
Patch(M("LauncherView","OnHighContrastChanged"),style.ToArray());
// Shorten only menu animation/delay constants, with no change to input timers.
foreach(var m in methods.Where(m=>m.DeclaringType.Name is "LauncherView" or "ViewController" or "FluxLauncherList")){
 foreach(var ins in m.Body.Instructions.Where(i=>i.OpCode==OpCodes.Ldc_I4 && i.Operand is int n && n is 1500 or 667 or 683)){
  int o=Start(m)+ins.Offset;
  // A method replaced above no longer uses its original offsets.
  if(changed.Contains(m.FullName))continue;
  BitConverter.GetBytes(180).CopyTo(bytes,o+1);changed.Add(m.FullName+" animation@"+ins.Offset);
 }
}
File.WriteAllBytes(args[1],bytes);
using var check=AssemblyDefinition.ReadAssembly(args[1]);
foreach(var m in check.MainModule.Types.SelectMany(t=>t.Methods).Where(m=>m.HasBody&&changed.Contains(m.FullName))){
 if(m.Body.ExceptionHandlers.Count!=0)throw new Exception("Unexpected retained exception handler");
 _=m.Body.Instructions.ToArray();
}
foreach(var getter in new[]{"get_EDEN_LAUNCHER_BG","get_EDEN_COMMON_BG"})Console.WriteLine(check.MainModule.Types.Single(t=>t.Name=="GUIDef").Methods.Single(m=>m.Name==getter).Body.Instructions.First().Operand);
File.WriteAllText(args[1]+".json",JsonSerializer.Serialize(new {original=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[0]))),patched=Convert.ToHexString(SHA256.HashData(bytes)),changes=changed},new JsonSerializerOptions{WriteIndented=true}));
Console.WriteLine("Verified "+changed.Count+" bounded method/constant edits.");
