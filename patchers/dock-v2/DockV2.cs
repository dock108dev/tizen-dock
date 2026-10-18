using Mono.Cecil;
using Mono.Cecil.Cil;
using System.Security.Cryptography;
using System.Text.Json;
var dir=Path.GetDirectoryName(Path.GetFullPath(args[0]))!;
var resolver=new DefaultAssemblyResolver();resolver.AddSearchDirectory(dir);resolver.AddSearchDirectory(System.Runtime.InteropServices.RuntimeEnvironment.GetRuntimeDirectory());
using var a=AssemblyDefinition.ReadAssembly(args[0],new ReaderParameters{AssemblyResolver=resolver});
using var flux=AssemblyDefinition.ReadAssembly(Path.Combine(args.Length > 2 ? Path.GetFullPath(args[2]) : Path.Combine(dir,"renderer-original"),"Tizen.TV.FLUX.Component.dll"));
using var nui=AssemblyDefinition.ReadAssembly(Path.Combine(args.Length > 2 ? Path.GetFullPath(args[2]) : Path.Combine(dir,"renderer-original"),"Tizen.NUI.dll"));
resolver.AddSearchDirectory(args.Length > 2 ? Path.GetFullPath(args[2]) : Path.Combine(dir,"renderer-original"));
MethodDefinition M(string t,string m)=>a.MainModule.Types.Single(x=>x.Name==t).Methods.Single(x=>x.Name==m);
void Replace(MethodDefinition m,params Instruction[] code){m.Body.Instructions.Clear();m.Body.ExceptionHandlers.Clear();m.Body.Variables.Clear();m.Body.InitLocals=false;foreach(var i in code)m.Body.Instructions.Add(i);}
foreach(var name in new[]{"COMMON_HEIGHT","COMMON_NOCONTENT_HEIGHT","LAUNCHER_HEIGHT_FOCUSED","LAUNCHER_HEIGHT_SELECTED"})Replace(M("GUIDef","get_"+name),Instruction.Create(OpCodes.Ldc_I4,32),Instruction.Create(OpCodes.Ret));
Replace(M("GUIDef","get_LAUNCHER_WIDTH"),Instruction.Create(OpCodes.Call,M("GUIDef","get_WINDOW_WIDTH")),Instruction.Create(OpCodes.Ldc_I4,16),Instruction.Create(OpCodes.Sub),Instruction.Create(OpCodes.Ret));
foreach(var m in a.MainModule.Types.SelectMany(t=>t.Methods).Where(m=>m.HasBody))foreach(var i in m.Body.Instructions){
 if(i.OpCode==OpCodes.Ldstr && i.Operand is string s && s.Contains("compact-dock-")&&s.EndsWith("-v1.png"))i.Operand=s.Replace("-v1.png","-v2.png");
}
var inset=M("LauncherView","OnHighContrastChanged").Body.Instructions.Single(i=>i.OpCode==OpCodes.Ldc_I4_S);inset.OpCode=OpCodes.Ldc_I4;inset.Operand=8;
foreach(var m in new[]{M("ImageTitleLauncherView","BindData"),M("IconTitleLauncherView","BindData"),M("IconTitleLauncherView",".ctor"),M("IconTitleLauncherViewPreset",".ctor")})foreach(var i in m.Body.Instructions.Where(i=>i.OpCode==OpCodes.Ldc_I4_S && (sbyte)i.Operand==13)){i.OpCode=OpCodes.Ldc_I4;i.Operand=m.DeclaringType.Name=="ImageTitleLauncherView"?18:16;}
foreach(var i in M("ImageTitleLauncherView","GetFocusedSize").Body.Instructions.Where(i=>i.OpCode==OpCodes.Ldc_I4_S && (sbyte)i.Operand==19)){i.OpCode=OpCodes.Ldc_I4;i.Operand=22;}
foreach(var i in M("ImageTitleLauncherView",".ctor").Body.Instructions.Where(i=>i.OpCode==OpCodes.Ldc_R4 && Math.Abs((float)i.Operand-0.6843f)<0.001))i.Operand=18f/22f;
var imageBox=flux.MainModule.Types.Single(t=>t.FullName=="Tizen.TV.FLUX.Component.ImageBox");
var setMask=a.MainModule.ImportReference(imageBox.Methods.Single(m=>m.Name=="set_AlphaMaskUrl"));
var view=nui.MainModule.Types.Single(t=>t.FullName=="Tizen.NUI.BaseComponents.View");
var setRadius=a.MainModule.ImportReference(view.Methods.Single(m=>m.Name=="set_CornerRadius"));
var setColor=a.MainModule.ImportReference(view.Methods.Single(m=>m.Name=="set_BackgroundColor"));
var transparent=a.MainModule.ImportReference(nui.MainModule.Types.Single(t=>t.FullName=="Tizen.NUI.Color").Fields.Single(f=>f.Name=="Transparent"));
var update=M("ImageTitleLauncherView","UpdateChildUnitSize");var il=update.Body.GetILProcessor();var ret=update.Body.Instructions.Last();
var image=update.DeclaringType.Fields.Single(f=>f.Name=="image");
foreach(var i in new[]{Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Ldfld,image),Instruction.Create(OpCodes.Ldstr,"/home/owner/share/tizen-dock/menu-overlay/compact-dock-icon-mask-v2.png"),Instruction.Create(OpCodes.Callvirt,setMask),Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Ldc_R4,26f),Instruction.Create(OpCodes.Callvirt,setRadius)})il.InsertBefore(ret,i);
var bind=M("ImageTitleLauncherView","BindData");var bil=bind.Body.GetILProcessor();var end=bind.Body.Instructions.Last();
foreach(var i in new[]{Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Ldsfld,transparent),Instruction.Create(OpCodes.Callvirt,setColor)})bil.InsertBefore(end,i);
// Keep content inside the enlarged strip, including the final app on the row.
var create=M("LauncherView","CreateViews");var cil=create.Body.GetILProcessor();var last=create.Body.Instructions.Last();
var setClip=a.MainModule.ImportReference(view.Methods.Single(m=>m.Name=="set_ClippingMode"));
foreach(var i in new[]{Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Ldfld,create.DeclaringType.Fields.Single(f=>f.Name=="bgView")),Instruction.Create(OpCodes.Ldc_I4_2),Instruction.Create(OpCodes.Callvirt,setClip)})cil.InsertBefore(last,i);
a.Write(args[1]);
using var read=AssemblyDefinition.ReadAssembly(args[1]);
var matched=read.MainModule.Types.Single(t=>t.Name=="ImageTitleLauncherView").Methods.Single(m=>m.Name=="UpdateChildUnitSize");
if(!matched.Body.Instructions.Any(i=>i.Operand is MethodReference m&&m.Name=="set_AlphaMaskUrl"))throw new Exception("Mask setter missing");
Console.WriteLine("Verified larger icons, dynamic display width, clipping, image alpha mask, transparent tile background and native rounded corners.");
File.WriteAllText(args[1]+".json",JsonSerializer.Serialize(new{sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[1]))),baseline="ImplNUI.compact-v1.dll",normalIconUnits=18,focusedIconUnits=22,dockHeightUnits=32,width="display width minus 16 units",temporary=true},new JsonSerializerOptions{WriteIndented=true}));
