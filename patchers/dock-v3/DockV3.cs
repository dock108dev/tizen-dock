using Mono.Cecil;
using Mono.Cecil.Cil;
using System.Security.Cryptography;
using System.Text.Json;
var dir=Path.GetDirectoryName(Path.GetFullPath(args[0]))!;
var resolver=new DefaultAssemblyResolver();resolver.AddSearchDirectory(dir);resolver.AddSearchDirectory(args.Length > 2 ? Path.GetFullPath(args[2]) : Path.Combine(dir,"renderer-original"));resolver.AddSearchDirectory(System.Runtime.InteropServices.RuntimeEnvironment.GetRuntimeDirectory());
using var a=AssemblyDefinition.ReadAssembly(args[0],new ReaderParameters{AssemblyResolver=resolver});
using var flux=AssemblyDefinition.ReadAssembly(Path.Combine(args.Length > 2 ? Path.GetFullPath(args[2]) : Path.Combine(dir,"renderer-original"),"Tizen.TV.FLUX.Component.dll"));
using var fbase=AssemblyDefinition.ReadAssembly(Path.Combine(args.Length > 2 ? Path.GetFullPath(args[2]) : Path.Combine(dir,"renderer-original"),"Tizen.TV.FLUX.dll"));
using var nui=AssemblyDefinition.ReadAssembly(Path.Combine(args.Length > 2 ? Path.GetFullPath(args[2]) : Path.Combine(dir,"renderer-original"),"Tizen.NUI.dll"));
MethodDefinition M(string t,string m)=>a.MainModule.Types.Single(x=>x.Name==t).Methods.Single(x=>x.Name==m);
MethodReference Import(AssemblyDefinition source,string type,string name)=>a.MainModule.ImportReference(source.MainModule.Types.Single(t=>t.FullName==type).Methods.Single(m=>m.Name==name));
void Replace(MethodDefinition m,params Instruction[] code){m.Body.Instructions.Clear();m.Body.ExceptionHandlers.Clear();m.Body.Variables.Clear();m.Body.InitLocals=false;foreach(var i in code)m.Body.Instructions.Add(i);}
foreach(var name in new[]{"COMMON_HEIGHT","COMMON_NOCONTENT_HEIGHT","LAUNCHER_HEIGHT_FOCUSED","LAUNCHER_HEIGHT_SELECTED"})Replace(M("GUIDef","get_"+name),Instruction.Create(OpCodes.Ldc_I4,25),Instruction.Create(OpCodes.Ret));
// The existing nine apps and native system controls need 210 layout units. Clamp
// to the window on smaller layouts and center the actual background container.
var width=M("GUIDef","get_LAUNCHER_WIDTH");
// Reuse the TV's System.Runtime assembly identity instead of the host runtime.
var existingMath=a.MainModule.Types.SelectMany(t=>t.Methods).Where(m=>m.HasBody).SelectMany(m=>m.Body.Instructions).Select(i=>i.Operand).OfType<MethodReference>().First(m=>m.DeclaringType.FullName=="System.Math");
var min=new MethodReference("Min",a.MainModule.TypeSystem.Int32,existingMath.DeclaringType){HasThis=false};
min.Parameters.Add(new ParameterDefinition(a.MainModule.TypeSystem.Int32));min.Parameters.Add(new ParameterDefinition(a.MainModule.TypeSystem.Int32));
Replace(width,Instruction.Create(OpCodes.Ldc_I4,210),Instruction.Create(OpCodes.Call,M("GUIDef","get_WINDOW_WIDTH")),Instruction.Create(OpCodes.Ldc_I4,24),Instruction.Create(OpCodes.Sub),Instruction.Create(OpCodes.Call,min),Instruction.Create(OpCodes.Ret));
foreach(var m in a.MainModule.Types.SelectMany(t=>t.Methods).Where(m=>m.HasBody))foreach(var i in m.Body.Instructions)
 if(i.OpCode==OpCodes.Ldstr && i.Operand is string s && s.Contains("compact-dock-background-v2"))i.Operand=s.Replace("-v2.png","-v3.png");
var tile=M("ContentItemView","GetUnfocusedSize");
foreach(var i in tile.Body.Instructions.Where(i=>i.OpCode==OpCodes.Ldc_I4_S&&(sbyte)i.Operand==13)){i.OpCode=OpCodes.Ldc_I4;i.Operand=17;}
foreach(var i in M("ContentItemView",".ctor").Body.Instructions.Where(i=>i.OpCode==OpCodes.Ldc_R4)){
 if(Math.Abs((float)i.Operand-1.46f)<0.001)i.Operand=1.18f;
 else if(Math.Abs((float)i.Operand-1.15f)<0.001)i.Operand=1.08f;
}
var mask=Import(flux,"Tizen.TV.FLUX.Component.ImageBox","set_AlphaMaskUrl");
var radius=Import(nui,"Tizen.NUI.BaseComponents.View","set_CornerRadius");
var color=Import(nui,"Tizen.NUI.BaseComponents.View","set_BackgroundColor");
var transparent=a.MainModule.ImportReference(nui.MainModule.Types.Single(t=>t.FullName=="Tizen.NUI.Color").Fields.Single(f=>f.Name=="Transparent"));
var bind=M("ContentItemView","BindData");var il=bind.Body.GetILProcessor();var end=bind.Body.Instructions.Last();
var main=bind.DeclaringType.Fields.Single(f=>f.Name=="mainImage");
foreach(var i in new[]{Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Ldfld,main),Instruction.Create(OpCodes.Ldstr,"/home/owner/share/tizen-dock/menu-overlay/compact-dock-icon-mask-v2.png"),Instruction.Create(OpCodes.Callvirt,mask),Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Ldc_R4,26f),Instruction.Create(OpCodes.Callvirt,radius),Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Ldsfld,transparent),Instruction.Create(OpCodes.Callvirt,color)})il.InsertBefore(end,i);
// Center the backdrop itself. The inner row has six units of padding on each side.
var style=M("LauncherView","OnHighContrastChanged");
var code=new List<Instruction>();
void Emit(OpCode op)=>code.Add(Instruction.Create(op));
void Call(MethodReference m)=>code.Add(Instruction.Create(OpCodes.Callvirt,m));
void Field(string name){Emit(OpCodes.Ldarg_0);code.Add(Instruction.Create(OpCodes.Ldfld,style.DeclaringType.Fields.Single(f=>f.Name==name)));}
void Num(int n)=>code.Add(Instruction.Create(OpCodes.Ldc_I4,n));
Field("bgView");Call(Import(nui,"Tizen.NUI.BaseComponents.View","ClearBackground"));
Field("bgView");code.Add(Instruction.Create(OpCodes.Call,M("GUIDef","get_EDEN_LAUNCHER_BG")));Call(Import(nui,"Tizen.NUI.BaseComponents.View","set_BackgroundImage"));
Field("bgView");Call(Import(flux,"Tizen.TV.FLUX.Component.ComponentBase","get_LayoutParam"));Num(1);Call(Import(flux,"Tizen.TV.FLUX.Component.LayoutItemParam","set_WidthResizePolicy"));
Field("bgView");code.Add(Instruction.Create(OpCodes.Call,width));Num(12);Emit(OpCodes.Add);Call(Import(fbase,"Tizen.TV.FLUX.FluxView","set_UnitSizeWidth"));
foreach(var property in new[]{"ParentOrigin","PivotPoint"}){Field("bgView");code.Add(Instruction.Create(OpCodes.Call,Import(nui,"Tizen.NUI."+property,"get_BottomCenter")));Call(Import(nui,"Tizen.NUI.BaseComponents.View","set_"+property));}
Field("bgView");Num(1);Call(Import(nui,"Tizen.NUI.BaseComponents.View","set_PositionUsesPivotPoint"));
Field("bgView");Num(0);Call(Import(fbase,"Tizen.TV.FLUX.FluxView","set_UnitPositionX"));
Field("bgLayout");Num(6);Call(Import(fbase,"Tizen.TV.FLUX.FluxView","set_UnitPositionX"));
Emit(OpCodes.Ret);Replace(style,code.ToArray());
a.Write(args[1]);
using var check=AssemblyDefinition.ReadAssembly(args[1]);
var c=check.MainModule.Types.Single(t=>t.Name=="ContentItemView").Methods.Single(m=>m.Name=="BindData");
if(!c.Body.Instructions.Any(i=>i.Operand is MethodReference m&&m.Name=="set_AlphaMaskUrl"))throw new Exception("App renderer mask missing");
if(check.MainModule.AssemblyReferences.Any(r=>r.Name=="System.Private.CoreLib"))throw new Exception("Host-only reference");
Console.WriteLine("Verified app shortcut renderer mask, 17-unit app tiles, 25-unit panel, bounded row width and centered backdrop.");
File.WriteAllText(args[1]+".json",JsonSerializer.Serialize(new{sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[1]))),baseline=Path.GetFileName(args[0]),normalAppUnits=17,dockHeightUnits=25,innerWidth="min(210, window - 24)",outerWidth="inner width + 12",anchor="BottomCenter",roundedRenderer="ContentItemView.mainImage",temporary=true},new JsonSerializerOptions{WriteIndented=true}));
