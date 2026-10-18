using Mono.Cecil;
using System.Reflection.PortableExecutable;
if(args.Length!=3) throw new Exception("input output full-type-name");
using var asm=AssemblyDefinition.ReadAssembly(args[0]);
IEnumerable<TypeDefinition> All(IEnumerable<TypeDefinition> ts) { foreach(var t in ts) {yield return t; foreach(var n in All(t.NestedTypes))yield return n;} }
var type=All(asm.MainModule.Types).Single(t=>t.FullName==args[2]);
bool hideAd=args[2].EndsWith("AdvertiseLauncherElement");
var method=hideAd ? type.Methods.Single(m=>m.Name=="GetUIJson") : type.Methods.Single(m=>m.Name=="GetItems" && m.Parameters.Count==1 && m.ReturnType.FullName=="System.Boolean" && m.Parameters[0].ParameterType.FullName=="System.String[]&");
if(!method.HasBody || method.Body.CodeSize<11)throw new Exception("Unexpected method body");
var str=asm.MainModule.GetTypeReferences().Single(t=>t.FullName=="System.String");
var bytes=File.ReadAllBytes(args[0]);
using var pe=new PEReader(new MemoryStream(bytes));
var section=pe.PEHeaders.SectionHeaders.Single(s=>method.RVA>=s.VirtualAddress && method.RVA<s.VirtualAddress+s.VirtualSize);
int offset=section.PointerToRawData+method.RVA-section.VirtualAddress;
byte[] body={0x2a,0x03,0x16,0x8d,0,0,0,0,0x51,0x17,0x2a};
BitConverter.GetBytes(str.MetadataToken.ToUInt32()).CopyTo(body,4);
if(hideAd) {
 var refs=method.Body.Instructions.Select(i=>i.Operand).ToArray();
 var parent=refs.OfType<MethodReference>().First(m=>m.Name=="get_Parent");
 var visible=refs.OfType<MethodReference>().First(m=>m.Name=="set_Visible");
 var empty=refs.OfType<FieldReference>().First(m=>m.Name=="JSON_STRING_EMPTY_OBJECT");
 body=new byte[]{0x4a,0x02,0x28,0,0,0,0,0x16,0x6f,0,0,0,0,0x7e,0,0,0,0,0x2a};
 BitConverter.GetBytes(parent.MetadataToken.ToUInt32()).CopyTo(body,3);
 BitConverter.GetBytes(visible.MetadataToken.ToUInt32()).CopyTo(body,9);
 BitConverter.GetBytes(empty.MetadataToken.ToUInt32()).CopyTo(body,14);
}
body.CopyTo(bytes,offset);File.WriteAllBytes(args[1],bytes);
using var check=AssemblyDefinition.ReadAssembly(args[1]);
var target=All(check.MainModule.Types).Single(t=>t.FullName==args[2]).Methods.Single(m=>m.Name==(hideAd ? "GetUIJson" : "GetItems"));
if(target.Body.Instructions.Count!=6 || target.Body.ExceptionHandlers.Count!=0)throw new Exception("Verification failed");
Console.WriteLine("Verified isolated method edit: "+target.FullName);
